#!/usr/bin/env python3
"""
Incremental ETL Sync: MySQL → PostgreSQL for Hunting License Application Data.

Unlike etl_pipeline.py (which does a full TRUNCATE + reload on every run), this
script performs *incremental* synchronisation:

  1. Reads the sync watermarks (max application_last_updated, max application_id)
     directly from the PostgreSQL destination table.
  2. Fetches ONLY rows from MySQL that are newer than those watermarks.
  3. UPSERTs each row into PostgreSQL using ON CONFLICT … DO UPDATE, so:
       • New rows are inserted.
       • Changed rows are updated.
       • Unchanged rows that appear again produce no effect (idempotent).
  4. Logs a before/after count summary to incremental_sync_log.txt (append mode).

Usage:
    python etl_incremental_sync.py                   # normal incremental run
    python etl_incremental_sync.py --yes             # skip prompt (non-interactive)
    python etl_incremental_sync.py --dry-run         # count delta only, no writes
    python etl_incremental_sync.py --force-full      # ignore watermarks, reload all (UPSERT)
    python etl_incremental_sync.py --batch-size 500  # override batch size

Dependencies:
    pip install mysql-connector-python psycopg2-binary sshtunnel
"""

import argparse
import logging
import os
import random
import sys
import time
from datetime import date, datetime

import mysql.connector
import psycopg2
from psycopg2.extras import execute_values
from sshtunnel import SSHTunnelForwarder

# ---------------------------------------------------------------------------
# SSH Tunnel Configuration
# ---------------------------------------------------------------------------
SSH_HOST     = '172.16.104.199'
SSH_PORT     = 22
SSH_USER     = 'hamzada'
SSH_PASSWORD = 'hamzaDAProd@ReplicaSupSet'

# ---------------------------------------------------------------------------
# Source Database Settings (MySQL)
# ---------------------------------------------------------------------------
SOURCE_HOST     = '172.16.104.199'
SOURCE_USER     = 'hamzaDAProdReplica'
SOURCE_PASSWORD = 'hamzaDAProd@ReplicaSupSet'
SOURCE_DB       = 'wildlife'

# ---------------------------------------------------------------------------
# Destination Database Settings (PostgreSQL)
# ---------------------------------------------------------------------------
PG_HOST     = '175.107.59.192'
PG_PORT     = 443
PG_DB       = 'postgres'
PG_USER     = 'hamza'
PG_PASSWORD = 'hcBgR8Rhg329tdO4ClZj!#'
PG_SCHEMA   = 'public'
PG_TABLE    = 'hunting_denormal'

# ---------------------------------------------------------------------------
# Composite unique key used for ON CONFLICT (must match a UNIQUE index in PG).
# ---------------------------------------------------------------------------
CONFLICT_COLUMNS = ['application_id', 'status_id', 'status_update_date']

# ---------------------------------------------------------------------------
# Columns that may change after initial insert and should be updated on conflict
# ---------------------------------------------------------------------------
UPDATE_COLUMNS = [
    'user_id', 'application_type_id', 'age', 'permanent_address', 'gender',
    'application_start_date', 'application_last_updated', 'status_title',
    'status_created_date', 'district_id', 'district_title', 'citizen_id',
    'profession_id', 'profession_title', 'qualification', 'total_amount',
    'payment_date', 'voucher_payment_status',
]

# ---------------------------------------------------------------------------
# Log file — append mode so history is preserved across runs
# ---------------------------------------------------------------------------
LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'incremental_sync_log.txt'
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logger = logging.getLogger('ETL_IncrementalSync')
logger.setLevel(logging.INFO)

c_handler = logging.StreamHandler(
    open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace', closefd=False)
    if hasattr(sys.stdout, 'fileno') else sys.stdout
)
c_handler.setLevel(logging.INFO)
c_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(c_handler)

f_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
f_handler.setLevel(logging.INFO)
f_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(f_handler)

# ---------------------------------------------------------------------------
# Base source query — updated to avoid inaccessible cross-database joins
# ---------------------------------------------------------------------------
BASE_SOURCE_QUERY = """
SELECT
    a.id AS application_id,
    a.user_id,
    a.application_type_id,
    TIMESTAMPDIFF(
        YEAR,
        a.applicant_dob,
        CURDATE()
    ) AS age,
    a.permanent_address,
    CASE 
        WHEN a.applicant_gender_id = 1 THEN 'Male'
        WHEN a.applicant_gender_id = 2 THEN 'Female'
        WHEN a.applicant_gender_id = 3 THEN 'Transgender'
        ELSE NULL
    END AS gender,
    DATE(a.created_at) AS application_start_date,
    DATE(ah.updated_at) AS application_last_updated,
    st.id AS status_id,
    st.title AS status_title,
    DATE(ah.created_at) AS status_created_date,
    DATE(ah.updated_at) AS status_update_date,
    NULL AS district_id,
    NULL AS district_title,
    NULL AS citizen_id,
    NULL AS profession_id,
    NULL AS profession_title,
    NULL AS qualification,
    v.total_amount,
    v.payment_date,
    v.voucher_payment_status
FROM applications a
LEFT JOIN application_histories ah
    ON a.id = ah.application_id
INNER JOIN vouchers v
    ON a.id = v.application_id
LEFT JOIN statuses st
    ON st.id = ah.status_id
WHERE v.payment_date IS NOT NULL
  AND v.voucher_payment_status = 'paid'
"""

# All columns in the order returned by BASE_SOURCE_QUERY
COLUMNS_LIST = [
    'application_id', 'user_id', 'application_type_id', 'age', 'permanent_address',
    'gender', 'application_start_date', 'application_last_updated', 'status_id',
    'status_title', 'status_created_date', 'status_update_date', 'district_id',
    'district_title', 'citizen_id', 'profession_id', 'profession_title',
    'qualification', 'total_amount', 'payment_date', 'voucher_payment_status',
]


def parse_args():
    parser = argparse.ArgumentParser(
        description='Incremental ETL Sync: MySQL → PostgreSQL for Hunting Licenses'
    )
    parser.add_argument(
        '--batch-size', type=int, default=500,
        help='Rows per INSERT batch (default: 500)'
    )
    parser.add_argument(
        '-y', '--yes', action='store_true',
        help='Skip interactive confirmation prompt'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Count delta rows and log them, but do NOT write anything to PostgreSQL'
    )
    parser.add_argument(
        '--force-full', action='store_true',
        help='Ignore watermarks and process all source rows (UPSERT, no truncate)'
    )
    return parser.parse_args()


def open_ssh_tunnel(max_retries=3):
    """Establish SSH tunnel with retries."""
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Opening SSH Tunnel to {SSH_USER}@{SSH_HOST}:{SSH_PORT}...")
            tunnel = SSHTunnelForwarder(
                (SSH_HOST, SSH_PORT),
                ssh_username=SSH_USER,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=("127.0.0.1", 3306),
                set_keepalive=15.0
            )
            tunnel.start()
            logger.info(f"✔ SSH Tunnel active on local port {tunnel.local_bind_port}")
            return tunnel
        except Exception as e:
            logger.warning(f"SSH Tunnel attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                raise
            time.sleep(2)


def connect_mysql(local_port, retries=5, backoff=1.0):
    """Establishes MySQL connection through SSH tunnel with retry logic."""
    attempt = 0
    while True:
        try:
            conn = mysql.connector.connect(
                host='127.0.0.1',
                port=local_port,
                user=SOURCE_USER,
                password=SOURCE_PASSWORD,
                database=SOURCE_DB,
                connection_timeout=300,
            )
            logger.info('[SUCCESS] Connected to MySQL database via SSH tunnel.')
            return conn
        except mysql.connector.Error as e:
            attempt += 1
            if attempt > retries:
                logger.critical(f'Failed to connect to MySQL database after {retries} attempts: {e}')
                raise
            wait = backoff * (2 ** (attempt - 1)) + random.random()
            logger.warning(f'MySQL connection error ({e}); retrying in {wait:.1f}s (attempt {attempt}/{retries})')
            time.sleep(wait)


def connect_pg(retries=5, backoff=1.0):
    """Establishes PostgreSQL connection with retry logic."""
    attempt = 0
    while True:
        try:
            conn = psycopg2.connect(
                host=PG_HOST,
                port=PG_PORT,
                database=PG_DB,
                user=PG_USER,
                password=PG_PASSWORD,
                sslmode='require',
                connect_timeout=300,
            )
            logger.info('[SUCCESS] Connected to PostgreSQL database.')
            return conn
        except psycopg2.Error as e:
            attempt += 1
            if attempt > retries:
                logger.critical(f'Failed to connect to PostgreSQL database after {retries} attempts: {e}')
                raise
            wait = backoff * (2 ** (attempt - 1)) + random.random()
            logger.warning(f'PG connection error ({e}); retrying in {wait:.1f}s (attempt {attempt}/{retries})')
            time.sleep(wait)


def read_sync_watermarks(pg_cursor):
    """Reads the current sync state from the PostgreSQL destination table."""
    pg_cursor.execute(
        f"""
        SELECT
            MAX(application_last_updated),
            MAX(application_id::bigint),
            COUNT(*)
        FROM {PG_SCHEMA}.{PG_TABLE}
        """
    )
    row = pg_cursor.fetchone()
    last_updated, last_id, row_count = row
    return last_updated, last_id, row_count


def build_incremental_query(last_updated_watermark, last_id_watermark, force_full):
    """Constructs the MySQL query that fetches only the delta (new/changed rows)."""
    base = BASE_SOURCE_QUERY.rstrip().rstrip(';')

    if force_full or last_updated_watermark is None:
        logger.info('Watermark: NONE detected — performing full load (UPSERT mode).')
        return base

    if isinstance(last_updated_watermark, (date, datetime)):
        watermark_str = last_updated_watermark.strftime('%Y-%m-%d')
    else:
        watermark_str = str(last_updated_watermark)

    delta_filter = f"""
  AND (
      DATE(ah.updated_at) > '{watermark_str}'
      OR a.id > {last_id_watermark}
  )"""

    logger.info(
        f'Watermark: last_updated={watermark_str}, last_id={last_id_watermark} '
        f'— fetching rows newer than these values.'
    )
    return base + delta_filter


def build_upsert_query():
    """Builds a PostgreSQL UPSERT statement using ON CONFLICT … DO UPDATE SET."""
    conflict_target = ', '.join(CONFLICT_COLUMNS)
    update_assignments = ',\n                '.join(
        f'{col} = EXCLUDED.{col}' for col in UPDATE_COLUMNS
    )
    return f"""
        INSERT INTO {PG_SCHEMA}.{PG_TABLE} ({', '.join(COLUMNS_LIST)})
        VALUES %s
        ON CONFLICT ({conflict_target})
        DO UPDATE SET
                {update_assignments}
    """


def clean_row(row):
    """Converts empty strings to NULL; leaves all other types intact."""
    return tuple(None if val == '' else val for val in row)


def run_incremental_sync(batch_size, dry_run, force_full, yes_flag):
    tunnel     = None
    mysql_conn = None
    pg_conn    = None

    logger.info('=' * 80)
    logger.info('STARTING HUNTING LICENSES INCREMENTAL ETL SYNC: MySQL -> PostgreSQL')
    logger.info(f'Source DB  : {SOURCE_HOST} / {SOURCE_DB}')
    logger.info(f'Destination: {PG_SCHEMA}.{PG_TABLE} on {PG_HOST}')
    logger.info(f'Batch Size : {batch_size}')
    logger.info(f'Dry Run    : {dry_run}')
    logger.info(f'Force Full : {force_full}')
    logger.info('=' * 80)

    start_time = time.time()

    try:
        # STEP 1 — Open SSH Tunnel & Connect Databases
        tunnel = open_ssh_tunnel()
        logger.info('Connecting to MySQL source database via SSH tunnel...')
        mysql_conn   = connect_mysql(tunnel.local_bind_port)
        mysql_cursor = mysql_conn.cursor()

        logger.info('Connecting to PostgreSQL destination database...')
        pg_conn    = connect_pg()
        pg_cursor  = pg_conn.cursor()

        # STEP 2 — Read sync watermarks from PostgreSQL
        logger.info('Reading sync watermarks from PostgreSQL destination table...')
        last_updated_wm, last_id_wm, pg_count_before = read_sync_watermarks(pg_cursor)
        logger.info(f'  Rows currently in PG       : {pg_count_before:,}')
        logger.info(f'  Last application_last_updated: {last_updated_wm}')
        logger.info(f'  Last application_id          : {last_id_wm}')

        # STEP 3 — Build the incremental (delta) MySQL query
        incremental_query = build_incremental_query(last_updated_wm, last_id_wm, force_full)

        # STEP 4 — Count delta rows
        logger.info('Counting delta rows in MySQL (incremental filter applied)...')
        count_start = time.time()
        mysql_cursor.execute(f'SELECT COUNT(*) FROM ({incremental_query}) AS src')
        delta_count = mysql_cursor.fetchone()[0]
        mysql_cursor.fetchall()  # Consume unread result
        logger.info(
            f'Delta row count: {delta_count:,} '
            f'(query took {time.time() - count_start:.2f}s)'
        )

        if delta_count == 0:
            logger.info(
                'No new or updated rows found in MySQL since last sync. '
                'PostgreSQL is already up to date. Exiting gracefully.'
            )
            return

        if dry_run:
            logger.info(
                f'[DRY RUN] Would upsert {delta_count:,} rows into '
                f'{PG_SCHEMA}.{PG_TABLE}. No changes made.'
            )
            return

        # STEP 5 — Ensure UNIQUE index exists for ON CONFLICT target
        logger.info('Ensuring UNIQUE index exists for ON CONFLICT target...')
        try:
            pg_cursor.execute(f"""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_hunting_denormal_conflict_key
                ON {PG_SCHEMA}.{PG_TABLE} (
                    application_id,
                    status_id,
                    status_update_date
                )
            """)
            pg_conn.commit()
            logger.info('[SUCCESS] UNIQUE index verified / created.')
        except psycopg2.errors.UniqueViolation:
            pg_conn.rollback()
            logger.warning('Duplicate rows found in PostgreSQL. Deduplicating legacy rows...')
            pg_cursor.execute(f"""
                DELETE FROM {PG_SCHEMA}.{PG_TABLE}
                WHERE ctid NOT IN (
                    SELECT MIN(ctid)
                    FROM {PG_SCHEMA}.{PG_TABLE}
                    GROUP BY application_id, status_id, status_update_date
                )
            """)
            pg_conn.commit()
            pg_cursor.execute(f"""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_hunting_denormal_conflict_key
                ON {PG_SCHEMA}.{PG_TABLE} (
                    application_id,
                    status_id,
                    status_update_date
                )
            """)
            pg_conn.commit()
            logger.info('[SUCCESS] Deduplicated legacy rows & created UNIQUE index.')

        # STEP 6 — Fetch delta rows from MySQL and UPSERT into PostgreSQL
        logger.info('Executing incremental source query on MySQL...')
        query_start = time.time()
        mysql_cursor.execute(incremental_query)
        logger.info(
            f'Source query executed (took {time.time() - query_start:.2f}s). '
            f'Starting batch upsert...'
        )

        upsert_query   = build_upsert_query()
        rows_processed = 0
        batch_count    = 0

        while True:
            batch = mysql_cursor.fetchmany(batch_size)
            if not batch:
                break

            batch_count += 1
            cleaned_batch = [clean_row(row) for row in batch]

            unique_batch = {}
            for row in cleaned_batch:
                key = (row[0], row[8], row[11])
                unique_batch[key] = row
            deduped_batch = list(unique_batch.values())

            execute_values(pg_cursor, upsert_query, deduped_batch)
            pg_conn.commit()

            rows_processed += len(batch)
            progress = (rows_processed / delta_count) * 100
            logger.info(
                f'  Batch {batch_count:3d} | Upserted {rows_processed:,} / '
                f'{delta_count:,} rows ({progress:.1f}%)'
            )

        logger.info('[SUCCESS] Batch upsert phase completed.')

        # STEP 7 — Post-sync validation
        logger.info('Running post-sync validation...')
        pg_cursor.execute(f'SELECT COUNT(*) FROM {PG_SCHEMA}.{PG_TABLE}')
        pg_count_after = pg_cursor.fetchone()[0]

        net_change = pg_count_after - pg_count_before
        logger.info(f'  Rows in PG before sync : {pg_count_before:,}')
        logger.info(f'  Rows in PG after  sync : {pg_count_after:,}')
        logger.info(f'  Net row change         : {net_change:+,}')
        logger.info(f'  Delta rows processed   : {rows_processed:,}')

        if net_change < 0:
            logger.warning(
                'Unexpected: PG row count decreased after sync. '
                'Investigate whether rows were deleted externally.'
            )
        else:
            logger.info('[SUCCESS] Post-sync validation passed.')

        # STEP 8 — Final summary
        elapsed = time.time() - start_time
        logger.info('=' * 80)
        logger.info('INCREMENTAL SYNC COMPLETED SUCCESSFULLY!')
        logger.info(f'  Delta Rows Processed   : {rows_processed:,}')
        logger.info(f'  New Rows Inserted      : {net_change:+,}  (updates counted as 0)')
        logger.info(f'  Total Execution Time   : {elapsed:.2f}s')
        logger.info(f'  Log appended to        : {LOG_FILE}')
        logger.info('=' * 80)

    except Exception as e:
        logger.error(f'Incremental sync encountered a critical error: {e}', exc_info=True)
        if pg_conn:
            logger.info('Rolling back any uncommitted PostgreSQL transactions...')
            pg_conn.rollback()
        sys.exit(1)

    finally:
        if mysql_conn and mysql_conn.is_connected():
            mysql_cursor.close()
            mysql_conn.close()
            logger.info('MySQL connection closed.')
        if pg_conn and not pg_conn.closed:
            pg_cursor.close()
            pg_conn.close()
            logger.info('PostgreSQL connection closed.')
        if tunnel:
            tunnel.stop()
            logger.info('SSH Tunnel closed.')


if __name__ == '__main__':
    args = parse_args()
    run_incremental_sync(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        force_full=args.force_full,
        yes_flag=args.yes,
    )
