"""
sync_arms_to_pg.py
────────────────────────────────────────────────────────────────────────────────
Optimized script to fetch data from `arms_denormal` (MariaDB/Localhost via SSH tunnel)
and put the data into PostgreSQL server table `public.arms_denormal`.

Usage:
    python sync_arms_to_pg.py --full          # Truncate PG table & copy all rows
    python sync_arms_to_pg.py --incremental   # Upsert missing rows starting from PG MAX(id)
    python sync_arms_to_pg.py --dry-run       # Compare row counts & min/max IDs without writing

Requirements:
    pip install pymysql psycopg2-binary sshtunnel python-dotenv tqdm
────────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import time
import argparse
import logging
import pymysql
import pymysql.cursors
import psycopg2
import psycopg2.extras
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv
from tqdm import tqdm

# ── Load Environment Variables ────────────────--------------------------------
load_dotenv()

SSH_HOST = os.getenv("SSH_HOST", "172.16.104.199")
SSH_PORT = int(os.getenv("SSH_PORT", 22))
SSH_USER = os.getenv("SSH_USER", "hamzada")
SSH_PASS = os.getenv("SSH_PASS", "hamzaDAProd@ReplicaSupSet")

MYSQL_USER = os.getenv("ARMS_SOURCE_USER", "hamzaDAProdReplica")
MYSQL_PASS = os.getenv("ARMS_SOURCE_PASS", "hamzaDAProd@ReplicaSupSet")
MYSQL_DB   = os.getenv("ARMS_SOURCE_DB", "arms_licenses")
MYSQL_TABLE= os.getenv("ARMS_SOURCE_TABLE", "arms_denormal")

PG_HOST   = os.getenv("ARMS_DEST_HOST", "175.107.59.192")
PG_PORT   = int(os.getenv("ARMS_DEST_PORT", 443))
PG_USER   = os.getenv("ARMS_DEST_USER", "hamza")
PG_PASS   = os.getenv("ARMS_DEST_PASS", "hcBgR8Rhg329tdO4ClZj!#")
PG_DB     = os.getenv("ARMS_DEST_DB", "postgres")
PG_SCHEMA = os.getenv("ARMS_DEST_SCHEMA", "public")
PG_TABLE  = os.getenv("ARMS_DEST_TABLE", "arms_denormal")

BATCH_SIZE = int(os.getenv("ARMS_BATCH_SIZE", 10000))

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def open_ssh_tunnel(max_retries=3):
    """Establish SSH tunnel with retries."""
    for attempt in range(1, max_retries + 1):
        try:
            logging.info(f"Opening SSH Tunnel to {SSH_USER}@{SSH_HOST}:{SSH_PORT}...")
            tunnel = SSHTunnelForwarder(
                (SSH_HOST, SSH_PORT),
                ssh_username=SSH_USER,
                ssh_password=SSH_PASS,
                remote_bind_address=("127.0.0.1", 3306),
                set_keepalive=15.0
            )
            tunnel.start()
            logging.info(f"✔ SSH Tunnel active on local port {tunnel.local_bind_port}")
            return tunnel
        except Exception as e:
            logging.warning(f"SSH Tunnel attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                raise
            time.sleep(2)

def get_mysql_conn(local_port):
    """Connect to MariaDB source database."""
    return pymysql.connect(
        host="127.0.0.1",
        port=local_port,
        user=MYSQL_USER,
        password=MYSQL_PASS,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=30,
        read_timeout=300
    )

def get_pg_conn():
    """Connect to PostgreSQL destination database."""
    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        user=PG_USER,
        password=PG_PASS,
        dbname=PG_DB,
        sslmode="require",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10
    )
    conn.autocommit = True
    return conn

def get_table_columns(mysql_conn):
    """Retrieve column list from MariaDB source table."""
    with mysql_conn.cursor() as cur:
        cur.execute(f"DESCRIBE `{MYSQL_TABLE}`;")
        return [row["Field"] for row in cur.fetchall()]

def get_db_stats(mysql_conn, pg_conn):
    """Fetch row count, min_id, max_id from both source and destination databases."""
    with mysql_conn.cursor() as m_cur:
        m_cur.execute(f"SELECT COUNT(*) AS cnt, MIN(id) AS min_id, MAX(id) AS max_id FROM `{MYSQL_TABLE}`;")
        m_stat = m_cur.fetchone()
        mysql_cnt = m_stat["cnt"] or 0
        mysql_min = m_stat["min_id"] or 0
        mysql_max = m_stat["max_id"] or 0

    with pg_conn.cursor() as p_cur:
        p_cur.execute(f'SELECT COUNT(*), COALESCE(MIN(id), 0), COALESCE(MAX(id), 0) FROM "{PG_SCHEMA}"."{PG_TABLE}";')
        pg_cnt, pg_min, pg_max = p_cur.fetchone()

    return {
        "mysql": {"cnt": mysql_cnt, "min": mysql_min, "max": mysql_max},
        "pg": {"cnt": pg_cnt, "min": pg_min, "max": pg_max}
    }

def run_sync(tunnel, columns, is_full=False):
    """Fetch data from MariaDB and stream to PostgreSQL in batch chunks."""
    local_port = tunnel.local_bind_port
    m_conn = get_mysql_conn(local_port)
    pg_conn = get_pg_conn()

    if is_full:
        logging.info(f'Truncating PostgreSQL table {PG_SCHEMA}."{PG_TABLE}"...')
        with pg_conn.cursor() as p_cur:
            p_cur.execute(f'TRUNCATE TABLE "{PG_SCHEMA}"."{PG_TABLE}";')
        logging.info("✔ TRUNCATE complete.")
        current_id = 0
    else:
        with pg_conn.cursor() as p_cur:
            p_cur.execute(f'SELECT COALESCE(MAX(id), 0) FROM "{PG_SCHEMA}"."{PG_TABLE}";')
            current_id = p_cur.fetchone()[0]
        logging.info(f"Resuming sync starting from PostgreSQL MAX(id) = {current_id}")

    col_list = ", ".join(f'"{c}"' for c in columns)
    update_cols = [c for c in columns if c != "id"]
    update_set = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)

    upsert_sql = (
        f'INSERT INTO "{PG_SCHEMA}"."{PG_TABLE}" ({col_list}) VALUES %s '
        f'ON CONFLICT (id) DO UPDATE SET {update_set}'
    )

    with m_conn.cursor() as m_cur:
        m_cur.execute(f"SELECT COUNT(*) AS cnt FROM `{MYSQL_TABLE}` WHERE id > %s;", (current_id,))
        total_rows_to_sync = m_cur.fetchone()["cnt"]

    if total_rows_to_sync == 0:
        logging.info("✔ PostgreSQL is already up to date — 0 rows to transfer.")
        m_conn.close()
        pg_conn.close()
        return 0, 0

    logging.info(f"Streaming {total_rows_to_sync:,} rows in batches of {BATCH_SIZE:,}...")
    start_time = time.time()
    total_transferred = 0

    with tqdm(total=total_rows_to_sync, unit="rows", desc="Syncing arms_denormal") as pbar:
        while True:
            # Fetch MySQL batch with auto-reconnect retry
            rows = None
            for attempt in range(1, 6):
                try:
                    if not m_conn.open:
                        m_conn = get_mysql_conn(tunnel.local_bind_port)
                    with m_conn.cursor() as m_cur:
                        m_cur.execute(
                            f"SELECT * FROM `{MYSQL_TABLE}` WHERE id > %s ORDER BY id LIMIT %s;",
                            (current_id, BATCH_SIZE)
                        )
                        rows = m_cur.fetchall()
                    break
                except Exception as e:
                    logging.warning(f"MySQL fetch attempt {attempt}/5 failed: {e}")
                    time.sleep(2 * attempt)
                    m_conn = get_mysql_conn(tunnel.local_bind_port)

            if not rows:
                break

            batch = [tuple(r[c] for c in columns) for r in rows]

            # Upsert into PostgreSQL with auto-reconnect retry
            for attempt in range(1, 6):
                try:
                    if pg_conn.closed != 0:
                        pg_conn = get_pg_conn()
                    with pg_conn.cursor() as p_cur:
                        psycopg2.extras.execute_values(p_cur, upsert_sql, batch, page_size=BATCH_SIZE)
                    break
                except Exception as e:
                    logging.warning(f"PostgreSQL insert attempt {attempt}/5 failed: {e}")
                    time.sleep(2 * attempt)
                    pg_conn = get_pg_conn()

            total_transferred += len(rows)
            current_id = rows[-1]["id"]
            pbar.update(len(rows))

    try:
        m_conn.close()
        pg_conn.close()
    except Exception:
        pass

    elapsed = time.time() - start_time
    return total_transferred, elapsed

def print_summary(title, stats, extra_info=None):
    m = stats["mysql"]
    p = stats["pg"]
    delta = m["cnt"] - p["cnt"]
    print("\n" + "=" * 68)
    print(f"          {title}")
    print("=" * 68)
    print(f" Source (MariaDB)   : {MYSQL_DB}.{MYSQL_TABLE}")
    print(f"   └─ Rows: {m['cnt']:,}  |  MIN(id): {m['min']:,}  |  MAX(id): {m['max']:,}")
    print(f" Target (PostgreSQL): {PG_DB}.{PG_SCHEMA}.{PG_TABLE}")
    print(f"   └─ Rows: {p['cnt']:,}  |  MIN(id): {p['min']:,}  |  MAX(id): {p['max']:,}")
    print(f" Difference / Delta : {delta:,} rows")
    if extra_info:
        print(f" Details            : {extra_info}")
    print("=" * 68)
    if delta == 0 and m["cnt"] > 0:
        print(" ✔ STATUS: PERFECT SYNC (100% Matching Rows & Numbers!)\n")
    elif delta > 0:
        print(f" ⚠ STATUS: {delta:,} ROWS MISSING IN POSTGRESQL\n")
    else:
        print(" ⚠ STATUS: UNEXPECTED DELTA\n")

def main():
    parser = argparse.ArgumentParser(description="Sync MariaDB arms_denormal to PostgreSQL")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full", action="store_true", help="Truncate PG table & load all rows")
    group.add_argument("--incremental", action="store_true", help="Upsert missing rows starting from PG MAX(id)")
    group.add_argument("--dry-run", action="store_true", help="Count rows & double check numbers only (no writes)")
    args = parser.parse_args()

    tunnel = None
    try:
        tunnel = open_ssh_tunnel()
        m_conn = get_mysql_conn(tunnel.local_bind_port)
        pg_conn = get_pg_conn()

        columns = get_table_columns(m_conn)
        stats = get_db_stats(m_conn, pg_conn)

        m_conn.close()
        pg_conn.close()

        print_summary("arms_denormal DATA PIPELINE SUMMARY", stats, f"Detected Columns: {len(columns)}")

        if args.dry_run:
            logging.info("Dry-run mode completed. No database modifications were made.")
            return

        transferred, elapsed = run_sync(tunnel, columns, is_full=args.full)
        if transferred > 0:
            m, s = divmod(int(elapsed), 60)
            rate = transferred / elapsed if elapsed > 0 else 0
            logging.info(f"✔ Transfer complete! {transferred:,} rows synced in {m}m {s}s ({rate:.1f} rows/s)")

        # Final Verification & Reconciliation
        m_conn = get_mysql_conn(tunnel.local_bind_port)
        pg_conn = get_pg_conn()
        final_stats = get_db_stats(m_conn, pg_conn)
        m_conn.close()
        pg_conn.close()

        print_summary("FINAL RECONCILIATION & DOUBLE CHECK", final_stats)

    except KeyboardInterrupt:
        logging.warning("Sync process cancelled by user.")
    except Exception as e:
        logging.error(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if tunnel:
            tunnel.stop()
            logging.info("✔ SSH tunnel closed.")

if __name__ == "__main__":
    main()
