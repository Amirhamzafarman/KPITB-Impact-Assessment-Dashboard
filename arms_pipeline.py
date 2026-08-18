"""
arms_pipeline.py
────────────────────────────────────────────────────────────────────────────────
Syncs `arms_denormal` from MariaDB (arms_licenses DB, via SSH tunnel to
172.16.104.199) → PostgreSQL `public.arms_denormal`.

Run modes:
    python arms_pipeline.py --full          # TRUNCATE PG + copy all rows
    python arms_pipeline.py --incremental   # Upsert missing rows starting from PG MAX(id)
    python arms_pipeline.py --dry-run       # Count rows only, no DB writes

Requirements:
    pip install pymysql psycopg2-binary sshtunnel paramiko python-dotenv tqdm
────────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import math
import time
import logging
import argparse

import pymysql
import pymysql.cursors
import psycopg2
import psycopg2.extras
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv
from tqdm import tqdm

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BATCH_SIZE   = int(os.getenv("ARMS_BATCH_SIZE", 1500))
LOG_FILE     = "arms_pipeline.log"
SOURCE_TABLE = os.getenv("ARMS_SOURCE_TABLE", "arms_denormal_temp")
DEST_TABLE   = os.getenv("ARMS_DEST_TABLE", "arms_denormal")
DEST_SCHEMA  = os.getenv("ARMS_DEST_SCHEMA", "public")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   log.info(f"{GREEN}✔  {msg}{RESET}")
def warn(msg): log.warning(f"{YELLOW}⚠  {msg}{RESET}")
def err(msg):  log.error(f"{RED}✘  {msg}{RESET}")
def info(msg): log.info(f"{CYAN}ℹ  {msg}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. SSH TUNNEL & CONNECTIONS WITH AUTO-RECONNECT
# ─────────────────────────────────────────────────────────────────────────────

def open_ssh_tunnel():
    """Open SSH tunnel to the remote MariaDB server."""
    info("Opening SSH tunnel…")
    try:
        tunnel = SSHTunnelForwarder(
            (os.getenv("SSH_HOST"), int(os.getenv("SSH_PORT", 22))),
            ssh_username=os.getenv("SSH_USER"),
            ssh_password=os.getenv("SSH_PASS"),
            remote_bind_address=("localhost", 3306),
        )
        tunnel.start()
        ok(f"SSH tunnel open → local port {tunnel.local_bind_port}")
        return tunnel
    except Exception as e:
        err(f"SSH tunnel failed: {e}")
        raise


def ensure_tunnel(tunnel):
    """Ensure SSH tunnel is running and active, restart if dropped."""
    try:
        if tunnel is not None and tunnel.is_active:
            return tunnel
    except Exception:
        pass
    
    if tunnel:
        try:
            tunnel.stop()
        except Exception:
            pass
    return open_ssh_tunnel()


def get_mysql_conn(tunnel, dict_cursor: bool = True):
    cursor_class = (
        pymysql.cursors.DictCursor if dict_cursor
        else pymysql.cursors.Cursor
    )
    return pymysql.connect(
        host="127.0.0.1",
        port=tunnel.local_bind_port,
        user=os.getenv("ARMS_SOURCE_USER"),
        password=os.getenv("ARMS_SOURCE_PASS"),
        database=os.getenv("ARMS_SOURCE_DB", "arms_licenses"),
        connect_timeout=30,
        read_timeout=300,
        write_timeout=300,
        cursorclass=cursor_class,
    )


def get_pg_conn():
    conn = psycopg2.connect(
        host=os.getenv("ARMS_DEST_HOST"),
        port=int(os.getenv("ARMS_DEST_PORT", 443)),
        user=os.getenv("ARMS_DEST_USER"),
        password=os.getenv("ARMS_DEST_PASS"),
        dbname=os.getenv("ARMS_DEST_DB", "postgres"),
        connect_timeout=15,
        sslmode="require",
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
    conn.autocommit = True
    return conn

def connect_with_retry(get_conn_fn, name: str, max_attempts: int = 10):
    for attempt in range(1, max_attempts + 1):
        try:
            return get_conn_fn()
        except Exception as e:
            warn(f"{name} connection failed (attempt {attempt}/{max_attempts}): {e}")
            if attempt == max_attempts:
                raise
            time.sleep(2 * attempt)


# ─────────────────────────────────────────────────────────────────────────────
# 2. ROW COUNTS & WATERMARK
# ─────────────────────────────────────────────────────────────────────────────

def mysql_count(mysql_conn, where: str = "") -> int:
    with mysql_conn.cursor() as cur:
        sql = f"SELECT COUNT(*) as cnt FROM `{SOURCE_TABLE}`"
        if where:
            sql += f" WHERE {where}"
        cur.execute(sql)
        return cur.fetchone()["cnt"]


def pg_count(pg_conn) -> int:
    with pg_conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM {DEST_SCHEMA}."{DEST_TABLE}"')
        return cur.fetchone()[0]


def pg_max_id(pg_conn) -> int:
    with pg_conn.cursor() as cur:
        cur.execute(f'SELECT COALESCE(MAX(id), 0) FROM {DEST_SCHEMA}."{DEST_TABLE}"')
        return cur.fetchone()[0]


def get_columns(mysql_conn) -> list:
    with mysql_conn.cursor() as cur:
        cur.execute(f"DESCRIBE `{SOURCE_TABLE}`")
        rows = cur.fetchall()
    return [r["Field"] for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# 3. PRE-FLIGHT SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_preflight(mode: str, mysql_src_count: int, pg_dest_count: int,
                    watermark: int = None, new_rows: int = None):
    W = 62
    line = "═" * W

    title = "arms_pipeline.py  —  Pre-Flight Summary"
    pad   = (W - len(title)) // 2
    extra = W - pad - len(title)

    print(f"\n{BOLD}{CYAN}╔{line}╗")
    print(f"║{' ' * pad}{title}{' ' * extra}║")
    print(f"╠{line}╣{RESET}")

    mode_label = {
        "full":        "FULL LOAD  (truncate + copy all)",
        "incremental": "INCREMENTAL / RESUME  (upsert missing rows)",
        "dry_run":     "DRY RUN  (no DB writes)",
    }.get(mode, mode.upper())

    def p(label, value, c=""):
        print(f"║  {c}{label:<24s}{value}{RESET}")

    p("Mode",         mode_label)
    p("SSH Tunnel",   f"{os.getenv('SSH_USER')}@{os.getenv('SSH_HOST')}:{os.getenv('SSH_PORT')}")
    p("MySQL Source", f"{os.getenv('ARMS_SOURCE_DB')}.{SOURCE_TABLE}")
    p("  └─ Row count", f"{mysql_src_count:,}")
    p("PG Destination", f"{DEST_SCHEMA}.{DEST_TABLE}")

    if mode == "full":
        p("  └─ Row count", f"{pg_dest_count:,}  ← will be TRUNCATED", YELLOW)
        batches  = math.ceil(mysql_src_count / BATCH_SIZE)
        p("Batch size",       f"{BATCH_SIZE:,} rows")
        p("Est. batches",     f"{batches:,}")
        print(f"║")
        p("⚠  TRUNCATE", f"will delete all {pg_dest_count:,} PG rows first!", YELLOW)

    elif mode == "incremental":
        p("  └─ Row count",   f"{pg_dest_count:,}")
        p("PG MAX(id)",       f"{watermark:,}  (watermark / start id)")
        p("Missing rows to sync", f"{new_rows:,}  (id > {watermark:,})")
        if new_rows == 0:
            p("✔  Status", "Already in sync — nothing to do.", GREEN)

    elif mode == "dry_run":
        p("  └─ Row count",   f"{pg_dest_count:,}")
        p("Delta",            f"{mysql_src_count - pg_dest_count:,} rows missing in PG")
        p("ℹ  No writes",     "dry-run mode — DB untouched.", CYAN)

    print(f"{BOLD}{CYAN}╚{line}╝{RESET}\n")


# ─────────────────────────────────────────────────────────────────────────────
# 4. RESILIENT TRANSFER (AUTO-RESTARTING CONNECTIONS & TUNNEL)
# ─────────────────────────────────────────────────────────────────────────────

def run_sync(tunnel, columns: list, start_id: int, total_to_sync: int, is_full: bool = False):
    col_list    = ", ".join(f'"{c}"' for c in columns)
    update_cols = [c for c in columns if c != "id"]
    update_set  = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)

    upsert_sql = (
        f'INSERT INTO {DEST_SCHEMA}."{DEST_TABLE}" ({col_list}) VALUES %s '
        f'ON CONFLICT (id) DO UPDATE SET {update_set}'
    )

    current_id     = start_id
    total_upserted = 0
    start_time     = time.time()

    tunnel = ensure_tunnel(tunnel)
    mysql_conn = get_mysql_conn(tunnel)
    pg_conn    = get_pg_conn()

    if is_full:
        info("Truncating PG table…")
        with pg_conn.cursor() as pg_cur:
            pg_cur.execute(f'TRUNCATE TABLE {DEST_SCHEMA}."{DEST_TABLE}"')
        pg_conn.commit()
        ok("TRUNCATE done.")

    with tqdm(
        total=total_to_sync,
        unit="rows",
        desc=f"{GREEN}Syncing {SOURCE_TABLE}{RESET}",
        bar_format=(
            "{desc}  {bar}  {n_fmt}/{total_fmt} rows"
            "  [{rate_fmt}  ETA {remaining}]"
        ),
        colour="green",
    ) as pbar:
        while True:
            max_retries = 10
            rows = None

            for attempt in range(1, max_retries + 1):
                try:
                    # Make sure SSH tunnel & connections are alive before each query batch
                    tunnel = ensure_tunnel(tunnel)
                    if mysql_conn is None or not mysql_conn.open:
                        mysql_conn = get_mysql_conn(tunnel)
                    if pg_conn is None or pg_conn.closed != 0:
                        pg_conn = get_pg_conn()

                    # Fetch batch from MySQL using primary key index filter
                    with mysql_conn.cursor() as mysql_cur:
                        mysql_cur.execute(
                            f"SELECT * FROM `{SOURCE_TABLE}` WHERE id > %s "
                            f"ORDER BY id LIMIT %s",
                            (current_id, BATCH_SIZE),
                        )
                        rows = mysql_cur.fetchall()

                    if not rows:
                        break

                    # Insert batch into PostgreSQL
                    batch = [tuple(r[c] for c in columns) for r in rows]
                    with pg_conn.cursor() as pg_cur:
                        psycopg2.extras.execute_values(
                            pg_cur, upsert_sql, batch, page_size=BATCH_SIZE
                        )
                    pg_conn.commit()
                    break  # Successful batch processing

                except Exception as e:
                    warn(f"Network / connection error on batch starting id>{current_id} (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(5 * attempt)
                    # Close stale connections and force reconnect on next loop iteration
                    try:
                        if mysql_conn: mysql_conn.close()
                    except: pass
                    try:
                        if pg_conn: pg_conn.close()
                    except: pass
                    mysql_conn = None
                    pg_conn    = None

            if not rows:
                break

            total_upserted += len(rows)
            current_id      = rows[-1]["id"]
            pbar.update(len(rows))

    try:
        if mysql_conn: mysql_conn.close()
        if pg_conn: pg_conn.close()
    except: pass

    elapsed = time.time() - start_time
    return total_upserted, elapsed, tunnel


# ─────────────────────────────────────────────────────────────────────────────
# 5. VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def verify(tunnel):
    tunnel = ensure_tunnel(tunnel)
    mysql_conn = get_mysql_conn(tunnel)
    pg_conn    = get_pg_conn()
    src   = mysql_count(mysql_conn)
    dst   = pg_count(pg_conn)
    delta = src - dst
    c     = GREEN if delta == 0 else YELLOW

    print(f"\n{BOLD}── Verification ──────────────────────────────────────{RESET}")
    print(f"  MySQL rows  : {src:>12,}")
    print(f"  PG rows     : {dst:>12,}")
    print(f"  {c}Delta       : {delta:>+12,}{RESET}")

    if delta == 0:
        ok("Perfect sync — both sides match.")
    elif delta > 0:
        warn(f"{delta:,} rows missing in PG.")
    else:
        warn(f"PG has {abs(delta):,} MORE rows than MySQL.")
    print()

    mysql_conn.close()
    pg_conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="arms_denormal pipeline: MySQL (SSH) → PostgreSQL"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--full",        action="store_true", help="TRUNCATE PG and copy all rows from MySQL")
    group.add_argument("--incremental", action="store_true", help="Upsert missing rows starting from PG MAX(id)")
    group.add_argument("--dry-run",     action="store_true", help="Count rows only, no DB writes")
    parser.add_argument("-y", "--yes",   action="store_true", help="Automatically answer yes to prompts")
    args = parser.parse_args()

    tunnel = None
    try:
        tunnel     = open_ssh_tunnel()
        mysql_conn = connect_with_retry(lambda: get_mysql_conn(tunnel), "MySQL")
        pg_conn    = connect_with_retry(get_pg_conn, "PostgreSQL")

        columns         = get_columns(mysql_conn)
        mysql_src_count = mysql_count(mysql_conn)
        pg_dest_count   = pg_count(pg_conn)
        watermark       = pg_max_id(pg_conn)
        missing_rows    = mysql_count(mysql_conn, where=f"id > {watermark}")

        mysql_conn.close()
        pg_conn.close()

        if args.dry_run:
            print_preflight("dry_run", mysql_src_count, pg_dest_count)
            info("Dry-run complete. No changes made.")
            return

        if args.full:
            print_preflight("full", mysql_src_count, pg_dest_count)
            if not args.yes:
                ans = input(f"{YELLOW}Proceed with TRUNCATE + full load? [y/N]: {RESET}").strip().lower()
                if ans != "y":
                    warn("Aborted by user.")
                    return

            upserted, elapsed, tunnel = run_sync(tunnel, columns, start_id=0, total_to_sync=mysql_src_count, is_full=True)
            m, s = divmod(int(elapsed), 60)
            ok(f"Full load complete in {m}m {s}s — {upserted:,} rows inserted.")
            verify(tunnel)

        elif args.incremental:
            print_preflight("incremental", mysql_src_count, pg_dest_count,
                            watermark=watermark, new_rows=missing_rows)

            if missing_rows == 0:
                ok("Nothing to sync — PG is already up to date.")
                return

            if not args.yes:
                ans = input(f"{GREEN}Proceed with incremental upsert? [y/N]: {RESET}").strip().lower()
                if ans != "y":
                    warn("Aborted by user.")
                    return

            upserted, elapsed, tunnel = run_sync(tunnel, columns, start_id=watermark, total_to_sync=missing_rows, is_full=False)
            m, s = divmod(int(elapsed), 60)
            ok(f"Incremental sync complete in {m}m {s}s — {upserted:,} rows upserted.")
            verify(tunnel)

    except KeyboardInterrupt:
        warn("Interrupted (Ctrl+C).")

    except Exception as e:
        err(f"Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        if tunnel:
            try:
                tunnel.stop()
            except Exception: pass
            info("SSH tunnel closed.")


if __name__ == "__main__":
    main()
