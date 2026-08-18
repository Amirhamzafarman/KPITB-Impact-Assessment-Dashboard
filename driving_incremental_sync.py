#!/usr/bin/env python3
"""
driving_incremental_sync.py
───────────────────────────
Incremental sync: MySQL DL_Denormal_Applications_new  →  PostgreSQL driving_denormal

HOW IT WORKS
  1. Reads MAX(id) from the PostgreSQL destination table  (the watermark).
  2. Counts how many rows in MySQL have id > watermark   (the delta).
  3. Prints a clear pre-flight summary and asks for your approval.
  4. Streams ONLY those new rows to PostgreSQL in chunks via COPY.
  5. Validates row counts before & after, then logs a summary.

USAGE
  python driving_incremental_sync.py               # shows delta, asks approval
  python driving_incremental_sync.py --dry-run     # preview only, zero writes
  python driving_incremental_sync.py --yes         # skip prompt  (cron / CI)
  python driving_incremental_sync.py --force-full  # re-sync ALL rows safely
  python driving_incremental_sync.py --chunk-size 25000

REQUIREMENTS
  pip install mysql-connector-python psycopg2-binary sshtunnel
"""

import argparse
import csv
import datetime as dt
import io
import logging
import os
import random
import sys
import time

import mysql.connector
import psycopg2
from sshtunnel import SSHTunnelForwarder

# ══════════════════════════════════════════════════════════════════════════════
# ❶  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# SSH Tunnel
SSH_HOST     = '172.16.104.199'
SSH_PORT     = 22
SSH_USER     = 'hamzada'
SSH_PASSWORD = 'hamzaDAProd@ReplicaSupSet'

# MySQL source
MYSQL_HOST     = '172.16.104.199'
MYSQL_USER     = 'hamzaDAProdReplica'
MYSQL_PASSWORD = 'hamzaDAProd@ReplicaSupSet'
MYSQL_DB       = 'drivinglicenses'
MYSQL_TABLE    = 'DL_Denormal_Applications_new'

# PostgreSQL destination
PG_HOST     = '175.107.59.192'
PG_PORT     = 443
PG_USER     = 'hamza'
PG_PASSWORD = 'hcBgR8Rhg329tdO4ClZj!#'
PG_DB       = 'postgres'
PG_SCHEMA   = 'public'
PG_TABLE    = 'driving_denormal'

CHUNK_SIZE          = 50_000          # rows per ID-range window
PG_ADVISORY_LOCK    = 55667788        # prevents two concurrent runs

LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'driving_incremental_sync.log'
)

# ══════════════════════════════════════════════════════════════════════════════
# ❷  LOGGING
# ══════════════════════════════════════════════════════════════════════════════

logger = logging.getLogger('DrivingIncrementalSync')
logger.setLevel(logging.INFO)
_fmt = logging.Formatter('[%(asctime)s] %(levelname)-8s %(message)s',
                         datefmt='%Y-%m-%d %H:%M:%S')

# Console — UTF-8 safe on Windows
_ch = logging.StreamHandler(
    open(sys.stdout.fileno(), mode='w', encoding='utf-8',
         errors='replace', closefd=False)
    if hasattr(sys.stdout, 'fileno') else sys.stdout
)
_ch.setFormatter(_fmt)
logger.addHandler(_ch)

# File — append mode so every run is preserved
_fh = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
_fh.setFormatter(_fmt)
logger.addHandler(_fh)

# ══════════════════════════════════════════════════════════════════════════════
# ❸  CLI
# ══════════════════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description='Incremental sync: MySQL DL_Denormal_Applications_new → PG driving_denormal'
    )
    p.add_argument('--dry-run',     action='store_true',
                   help='Count new rows and show summary — no writes to PostgreSQL')
    p.add_argument('--yes',         action='store_true',
                   help='Skip the "Proceed? (yes/no)" prompt (use in cron / scripts)')
    p.add_argument('--force-full',  action='store_true',
                   help='Ignore watermark and re-sync ALL rows from MySQL (safe UPSERT)')
    p.add_argument('--chunk-size',  type=int, default=CHUNK_SIZE,
                   help=f'Rows per chunk (default: {CHUNK_SIZE:,})')
    return p.parse_args()

# ══════════════════════════════════════════════════════════════════════════════
# ❹  CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _open_ssh_tunnel(max_retries=3):
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


def _connect_mysql(local_port, retries=5, backoff=2.0):
    attempt = 0
    while True:
        try:
            conn = mysql.connector.connect(
                host='127.0.0.1', port=local_port, user=MYSQL_USER, password=MYSQL_PASSWORD,
                database=MYSQL_DB, connection_timeout=60, raw=False,
            )
            cur = conn.cursor()
            cur.execute("SET session net_read_timeout  = 600")
            cur.execute("SET session net_write_timeout = 600")
            cur.execute("SET session wait_timeout      = 28800")
            cur.close()
            return conn
        except mysql.connector.Error as e:
            attempt += 1
            if attempt > retries:
                raise
            wait = backoff * (2 ** (attempt - 1)) + random.random()
            logger.warning('MySQL connect failed (%s) — retry %d/%d in %.1fs', e, attempt, retries, wait)
            time.sleep(wait)


def _connect_pg(retries=5, backoff=2.0):
    attempt = 0
    while True:
        try:
            conn = psycopg2.connect(
                host=PG_HOST, port=PG_PORT, database=PG_DB,
                user=PG_USER, password=PG_PASSWORD,
                sslmode='require', connect_timeout=60,
            )
            return conn
        except psycopg2.Error as e:
            attempt += 1
            if attempt > retries:
                raise
            wait = backoff * (2 ** (attempt - 1)) + random.random()
            logger.warning('PG connect failed (%s) — retry %d/%d in %.1fs', e, attempt, retries, wait)
            time.sleep(wait)

# ══════════════════════════════════════════════════════════════════════════════
# ❺  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _q(name):
    """Double-quote a PostgreSQL identifier."""
    return '"' + name.replace('"', '""') + '"'

def _pg_tbl():
    return f'{_q(PG_SCHEMA)}.{_q(PG_TABLE)}'

def _normalize(value):
    """Serialize a Python value for PostgreSQL COPY TEXT format."""
    if value is None:
        return r'\N'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, bytes):
        return ('1' if value[0] else '0') if len(value) == 1 else value.hex()
    if isinstance(value, dt.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, dt.date):
        return value.strftime('%Y-%m-%d')
    s = str(value)
    s = s.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n').replace('\r', '\\r')
    return s

def _progress(done, total, t0, prefix='Progress:'):
    if total <= 0:
        return
    elapsed = time.time() - t0
    pct     = done / total * 100
    filled  = int(40 * done // total)
    bar     = '#' * filled + '-' * (40 - filled)
    speed   = done / elapsed if elapsed > 0 else 0
    eta     = (total - done) / speed if speed > 0 else 0
    eta_s   = (f'{int(eta//3600)}h{int((eta%3600)//60)}m' if eta >= 3600
               else f'{int(eta//60)}m{int(eta%60)}s' if eta >= 60
               else f'{int(eta)}s')
    tag     = f'Done in {elapsed:.1f}s' if done >= total else f'{speed:,.0f} r/s  ETA {eta_s}'
    try:
        sys.stdout.write(f'\r{prefix} |{bar}| {pct:.1f}%  {done:,}/{total:,}  [{tag}]')
        sys.stdout.flush()
    except UnicodeEncodeError:
        pass
    if done >= total:
        sys.stdout.write('\n')
        sys.stdout.flush()

# ══════════════════════════════════════════════════════════════════════════════
# ❻  SCHEMA  — fetch columns from MySQL, verify PG table is compatible
# ══════════════════════════════════════════════════════════════════════════════

def _mysql_columns(mysql_conn):
    cur = mysql_conn.cursor()
    cur.execute(f'DESCRIBE `{MYSQL_TABLE}`')
    cols = [(row[0], row[1]) for row in cur.fetchall()]
    cur.close()
    return cols                          # [(name, mysql_type), ...]


def _verify_pg_schema(pg_conn, mysql_cols):
    """
    Confirm:
      • driving_denormal exists in PostgreSQL.
      • Its column list matches MySQL source columns + source_table.
    Raises RuntimeError with a clear fix instruction on any mismatch.
    """
    cur = pg_conn.cursor()

    # table exists?
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        )
    """, (PG_SCHEMA, PG_TABLE))
    if not cur.fetchone()[0]:
        cur.close()
        raise RuntimeError(
            f'\n  ✗ Table {_pg_tbl()} does NOT exist in PostgreSQL.\n'
            '    Run sync_dl_denormal.py first to perform the initial full migration.\n'
        )

    # column order matches?
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (PG_SCHEMA, PG_TABLE))
    pg_cols    = [r[0] for r in cur.fetchall()]
    expected   = [c[0] for c in mysql_cols] + ['source_table']
    cur.close()

    if pg_cols != expected:
        missing = sorted(set(expected) - set(pg_cols))
        extra   = sorted(set(pg_cols)  - set(expected))
        raise RuntimeError(
            f'\n  ✗ Schema mismatch between MySQL source and PostgreSQL destination.\n'
            f'    Missing in PG : {missing or "none"}\n'
            f'    Extra in PG   : {extra or "none"}\n'
            '    Run sync_dl_denormal.py --reset to rebuild, then retry.\n'
        )

# ══════════════════════════════════════════════════════════════════════════════
# ❼  WATERMARK  — MAX(id) already in PostgreSQL
# ══════════════════════════════════════════════════════════════════════════════

def _read_watermark(pg_conn):
    """
    Returns (watermark_id, pg_row_count).
    watermark_id is None when the destination table is empty → triggers full load.
    """
    cur = pg_conn.cursor()
    cur.execute(f'SELECT MAX("id"::bigint), COUNT(*) FROM {_pg_tbl()}')
    wm, count = cur.fetchone()
    cur.close()
    return wm, count

# ══════════════════════════════════════════════════════════════════════════════
# ❽  DELTA  — how many new rows exist in MySQL since the watermark
# ══════════════════════════════════════════════════════════════════════════════

def _delta_info(mysql_conn, watermark_id, force_full):
    """
    Returns (start_id, mysql_max_id, delta_count).
    start_id is the first MySQL id we need to copy.
    """
    cur = mysql_conn.cursor()
    cur.execute(f'SELECT MIN(id), MAX(id) FROM `{MYSQL_TABLE}`')
    min_id, max_id = cur.fetchone()

    if min_id is None:                  # source table completely empty
        cur.close()
        return None, None, 0

    start_id = min_id if (force_full or watermark_id is None) else int(watermark_id) + 1

    if start_id > max_id:               # nothing new
        cur.close()
        return start_id, max_id, 0

    cur.execute(
        f'SELECT COUNT(*) FROM `{MYSQL_TABLE}` WHERE id >= %s AND id <= %s',
        (start_id, max_id)
    )
    delta_count = cur.fetchone()[0]
    cur.close()
    return start_id, max_id, delta_count

# ══════════════════════════════════════════════════════════════════════════════
# ❾  ADVISORY LOCK  — blocks a second concurrent run
# ══════════════════════════════════════════════════════════════════════════════

def _acquire_lock(pg_conn):
    cur = pg_conn.cursor()
    cur.execute('SELECT pg_try_advisory_lock(%s)', (PG_ADVISORY_LOCK,))
    ok = cur.fetchone()[0]
    cur.close()
    return ok

# ══════════════════════════════════════════════════════════════════════════════
# ❿  UNIQUE INDEX  — required so ON CONFLICT (id) works
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_unique_index(pg_conn):
    cur = pg_conn.cursor()
    cur.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_{PG_TABLE}_id
        ON {_pg_tbl()} ("id")
    """)
    pg_conn.commit()
    cur.close()

# ══════════════════════════════════════════════════════════════════════════════
# ⓫  APPROVAL GATE  — show summary, ask yes/no
# ══════════════════════════════════════════════════════════════════════════════

def _approval_gate(watermark_id, pg_count, start_id, mysql_max_id,
                   delta_count, force_full, dry_run, yes_flag):
    """
    Print the pre-flight summary.
    Returns True  → proceed with migration.
    Returns False → user declined, exit cleanly.
    """
    bar = '═' * 62
    logger.info(bar)
    logger.info('  DRIVING LICENSES — INCREMENTAL SYNC  PRE-FLIGHT SUMMARY')
    logger.info(bar)
    logger.info('  Source      : %s / %s.%s', MYSQL_HOST, MYSQL_DB, MYSQL_TABLE)
    logger.info('  Destination : %s.%s  on  %s', PG_SCHEMA, PG_TABLE, PG_HOST)
    logger.info(bar)
    logger.info('  Rows in PostgreSQL right now : %s', f'{pg_count:,}')
    if force_full:
        logger.info('  Sync mode                    : FORCE FULL (watermark ignored)')
    else:
        logger.info('  Watermark  MAX(id) in PG     : %s', watermark_id)
    logger.info('  MySQL max id                 : %s', mysql_max_id)
    logger.info('  ID range to migrate          : %s → %s', start_id, mysql_max_id)
    logger.info('  ── NEW ROWS FOUND IN MYSQL ─────── %s ──', f'{delta_count:,}')
    if dry_run:
        logger.info('  Mode                         : DRY RUN  (no writes)')
    logger.info(bar)

    if dry_run or delta_count == 0:
        return True                     # nothing to approve / dry-run always proceeds

    if yes_flag:
        logger.info('  --yes flag set — skipping confirmation prompt.')
        return True

    # ── Interactive approval ───────────────────────────────────────────────
    print()
    print(f'  ➜  About to insert {delta_count:,} new rows into {PG_SCHEMA}.{PG_TABLE}.')
    print()
    try:
        answer = input('  Type  yes  to proceed, anything else to abort: ').strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        logger.info('Prompt interrupted — aborting. No changes made.')
        return False

    if answer == 'yes':
        logger.info('Approved. Starting migration…')
        return True

    logger.info('Answer was "%s" — aborting. No changes made.', answer)
    return False

# ══════════════════════════════════════════════════════════════════════════════
# ⓬  STREAMING  — chunk-by-chunk COPY  with per-chunk retry
# ══════════════════════════════════════════════════════════════════════════════

def _stream_new_rows(mysql_conn, pg_conn, mysql_cols,
                     start_id, mysql_max_id, delta_count, chunk_size, tunnel_port):
    """
    Fetches rows WHERE id BETWEEN chunk_start AND chunk_end from MySQL
    and inserts them into PostgreSQL via:

        COPY → temp staging table
        INSERT … ON CONFLICT (id) DO NOTHING → destination

    The ON CONFLICT guard makes every chunk idempotent even if a chunk
    is retried after a partial failure.

    Returns the number of rows streamed from MySQL.
    """
    all_cols  = [c[0] for c in mysql_cols] + ['source_table']
    copy_cols = ', '.join(_q(c) for c in all_cols)
    sel_cols  = ', '.join(f'`{c[0]}`' for c in mysql_cols)

    staging_copy_sql = (
        f'COPY _drv_staging ({copy_cols}) '
        "FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\\\N')"
    )
    insert_sql = f"""
        INSERT INTO {_pg_tbl()} ({copy_cols})
        SELECT {copy_cols} FROM _drv_staging
        ON CONFLICT ("id") DO NOTHING
    """

    rows_streamed = 0
    current      = start_id
    t0           = time.time()

    _progress(0, delta_count, t0)

    while current <= mysql_max_id:
        chunk_end = current + chunk_size - 1
        query     = (f'SELECT {sel_cols} FROM `{MYSQL_TABLE}` '
                     f'WHERE id BETWEEN {current} AND {chunk_end}')

        # ── Fetch chunk (retry on MySQL connection loss) ───────────────────
        chunk = None
        for attempt in range(5):
            try:
                mc = mysql_conn.cursor()
                mc.execute(query)
                chunk = mc.fetchall()
                mc.close()
                break
            except Exception as exc:
                logger.warning('MySQL error fetching ids %d–%d (attempt %d/5): %s',
                               current, chunk_end, attempt + 1, exc)
                try:
                    mysql_conn.close()
                except Exception:
                    pass
                mysql_conn = _connect_mysql(local_port=tunnel_port)

        if chunk is None:
            raise RuntimeError(f'Failed to fetch chunk {current}–{chunk_end} after 5 attempts.')

        if chunk:
            # ── Serialize to TSV ───────────────────────────────────────────
            buf = io.StringIO()
            w   = csv.writer(buf, delimiter='\t', lineterminator='\n',
                             quoting=csv.QUOTE_NONE, escapechar='\\')
            for row in chunk:
                w.writerow([_normalize(v) for v in row] + [MYSQL_TABLE])
            buf.seek(0)

            # ── Write to PG (retry on PG connection loss) ──────────────────
            for pg_attempt in range(5):
                try:
                    pc = pg_conn.cursor()
                    # Per-transaction temp table: auto-cleared on COMMIT
                    pc.execute(f"""
                        CREATE TEMP TABLE IF NOT EXISTS _drv_staging
                        (LIKE {_pg_tbl()} INCLUDING ALL)
                        ON COMMIT DELETE ROWS
                    """)
                    pc.copy_expert(staging_copy_sql, buf)
                    pc.execute(insert_sql)
                    pg_conn.commit()
                    pc.close()
                    break
                except Exception as exc:
                    logger.warning('PG error on chunk %d–%d (attempt %d/5): %s',
                                   current, chunk_end, pg_attempt + 1, exc)
                    try:
                        pg_conn.rollback() if not pg_conn.closed else None
                        pg_conn.close()
                    except Exception:
                        pass
                    pg_conn = _connect_pg()
                    buf.seek(0)

            rows_streamed += len(chunk)
            _progress(rows_streamed, delta_count, t0)

        current += chunk_size

    return rows_streamed

# ══════════════════════════════════════════════════════════════════════════════
# ⓭  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    args = parse_args()

    logger.info('═' * 62)
    logger.info('  DRIVING LICENSES  —  INCREMENTAL SYNC STARTED')
    logger.info('  Dry Run: %-6s  Force Full: %-6s  Chunk: %s',
                args.dry_run, args.force_full, f'{args.chunk_size:,}')
    logger.info('═' * 62)

    run_start  = time.time()
    tunnel     = None
    mysql_conn = None
    pg_conn    = None

    try:
        # ── 1. SSH Tunnel & Connections ────────────────────────────────────
        tunnel = _open_ssh_tunnel()

        logger.info('Connecting to MySQL via SSH tunnel…')
        mysql_conn = _connect_mysql(local_port=tunnel.local_bind_port)
        logger.info('  ✔  MySQL connected.')

        logger.info('Connecting to PostgreSQL…')
        pg_conn = _connect_pg()
        logger.info('  ✔  PostgreSQL connected.')

        # ── 2. Concurrency guard (advisory lock) ───────────────────────────
        if not args.dry_run:
            if not _acquire_lock(pg_conn):
                logger.error(
                    'Another instance of this script appears to be running '
                    '(advisory lock held). Aborting to prevent duplicate rows.'
                )
                sys.exit(1)
            logger.info('  ✔  Advisory lock acquired.')

        # ── 3. Schema verification ─────────────────────────────────────────
        logger.info('Fetching MySQL schema…')
        mysql_cols = _mysql_columns(mysql_conn)
        logger.info('  ✔  Source table: %d columns.', len(mysql_cols))

        logger.info('Verifying PostgreSQL schema…')
        _verify_pg_schema(pg_conn, mysql_cols)
        logger.info('  ✔  Schema verified — PG matches MySQL.')

        # ── 4. Watermark ───────────────────────────────────────────────────
        logger.info('Reading watermark from PostgreSQL…')
        watermark_id, pg_count = _read_watermark(pg_conn)
        logger.info('  ✔  Watermark MAX(id) = %s  |  PG rows = %s',
                    watermark_id, f'{pg_count:,}')

        # ── 5. Delta detection ─────────────────────────────────────────────
        logger.info('Computing delta in MySQL…')
        start_id, mysql_max_id, delta_count = _delta_info(
            mysql_conn,
            watermark_id if not args.force_full else None,
            args.force_full,
        )
        logger.info('  ✔  Delta: %s new rows  (ids %s → %s)',
                    f'{delta_count:,}', start_id, mysql_max_id)

        # ── 6. Approval gate ───────────────────────────────────────────────
        proceed = _approval_gate(
            watermark_id, pg_count, start_id, mysql_max_id,
            delta_count, args.force_full, args.dry_run, args.yes,
        )
        if not proceed:
            sys.exit(0)

        # ── 7. Dry-run exit ────────────────────────────────────────────────
        if args.dry_run:
            logger.info('[DRY RUN] Would migrate %s rows into %s.%s. '
                        'No changes made.', f'{delta_count:,}', PG_SCHEMA, PG_TABLE)
            logger.info('[DRY RUN] Finished in %.2fs.', time.time() - run_start)
            return

        # ── 8. Nothing to do? ──────────────────────────────────────────────
        if delta_count == 0:
            logger.info('PostgreSQL is already up to date — nothing to migrate. ✔')
            return

        # ── 9. Ensure UNIQUE index on (id) ─────────────────────────────────
        logger.info('Ensuring UNIQUE index on (id) in destination…')
        _ensure_unique_index(pg_conn)
        logger.info('  ✔  UNIQUE index ready.')

        # ── 10. Stream new rows ────────────────────────────────────────────
        logger.info('Streaming %s new rows from MySQL → PostgreSQL…', f'{delta_count:,}')
        rows_sent = _stream_new_rows(
            mysql_conn, pg_conn, mysql_cols,
            start_id, mysql_max_id, delta_count, args.chunk_size, tunnel.local_bind_port
        )

        # ── 11. Validate ───────────────────────────────────────────────────
        logger.info('Running post-sync validation…')
        cur = pg_conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM {_pg_tbl()}')
        pg_count_after = cur.fetchone()[0]
        cur.close()

        net_new   = pg_count_after - pg_count
        skipped   = rows_sent - net_new          # absorbed by ON CONFLICT DO NOTHING

        logger.info('  Rows in PG before : %s', f'{pg_count:,}')
        logger.info('  Rows in PG after  : %s', f'{pg_count_after:,}')
        logger.info('  Net new rows      : %s', f'{net_new:+,}')
        logger.info('  Duplicate skips   : %s', f'{skipped:,}')

        if net_new < 0:
            logger.warning('UNEXPECTED: PG count decreased. Check for external deletions.')
        else:
            logger.info('  ✔  Validation passed.')

        # ── 12. ANALYZE ────────────────────────────────────────────────────
        cur = pg_conn.cursor()
        cur.execute(f'ANALYZE {_pg_tbl()}')
        pg_conn.commit()
        cur.close()
        logger.info('  ✔  ANALYZE complete.')

        # ── 13. Final summary ──────────────────────────────────────────────
        elapsed = time.time() - run_start
        logger.info('═' * 62)
        logger.info('  INCREMENTAL SYNC COMPLETE')
        logger.info('  New rows inserted : %s', f'{net_new:,}')
        logger.info('  Rows from MySQL   : %s', f'{rows_sent:,}')
        logger.info('  Dupe skips        : %s', f'{skipped:,}')
        logger.info('  Duration          : %.2fs', elapsed)
        logger.info('  Log file          : %s', LOG_FILE)
        logger.info('═' * 62)

    except Exception as exc:
        logger.error('Fatal error: %s', exc, exc_info=True)
        if pg_conn and not pg_conn.closed:
            try:
                pg_conn.rollback()
            except Exception:
                pass
        sys.exit(1)

    finally:
        try:
            if mysql_conn and mysql_conn.is_connected():
                mysql_conn.close()
                logger.info('MySQL connection closed.')
        except Exception:
            pass
        try:
            if pg_conn and not pg_conn.closed:
                pg_conn.close()
                logger.info('PostgreSQL connection closed.')
        except Exception:
            pass
        try:
            if tunnel:
                tunnel.stop()
                logger.info('SSH Tunnel closed.')
        except Exception:
            pass


if __name__ == '__main__':
    main()
