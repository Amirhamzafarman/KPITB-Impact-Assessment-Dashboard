"""
wildlife_pipeline.py
────────────────────────────────────────────────────────────────────────────────
Extracts data from MariaDB Replica → `wildlife` database and loads it into
PostgreSQL → `hunting_denormal` table.

Run:
    python wildlife_pipeline.py               # full load
    python wildlife_pipeline.py --incremental # only changed records since last run
    python wildlife_pipeline.py --dry-run     # extract only, skip DB write

Requirements:
    pip install -r requirements.txt
────────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import logging
import argparse
import datetime
import traceback

import pymysql
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

# ── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
BATCH_SIZE      = int(os.getenv("BATCH_SIZE", 500))      # rows per PG insert
WATERMARK_FILE  = ".wildlife_watermark"                   # stores last run timestamp
LOG_FILE        = "wildlife_pipeline.log"

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

# ── ANSI colour helpers (terminal only) ───────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    log.info(f"{GREEN}✔  {msg}{RESET}")
def warn(msg):  log.warning(f"{YELLOW}⚠  {msg}{RESET}")
def err(msg):   log.error(f"{RED}✘  {msg}{RESET}")
def info(msg):  log.info(f"{CYAN}ℹ  {msg}{RESET}")
def banner(msg):
    line = "─" * 70
    log.info(f"\n{BOLD}{CYAN}{line}\n  {msg}\n{line}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# 1. CONNECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_source_connection(dict_cursor: bool = True):
    """Connect to MariaDB Replica → wildlife database.
    
    Args:
        dict_cursor: If True, use DictCursor (for schema introspection).
                     If False, use plain Cursor (required for pd.read_sql).
                     pd.read_sql iterates rows as iterables; DictCursor returns
                     dicts, and iterating a dict yields its KEYS (column names),
                     not values — causing every value to be a column name string.
    """
    info("Connecting to MariaDB Replica (wildlife)…")
    try:
        cursor_class = (
            pymysql.cursors.DictCursor if dict_cursor
            else pymysql.cursors.Cursor
        )
        conn = pymysql.connect(
            host     = os.getenv("SOURCE_HOST"),
            port     = int(os.getenv("SOURCE_PORT", 3306)),
            user     = os.getenv("SOURCE_USER"),
            password = os.getenv("SOURCE_PASS"),
            database = os.getenv("SOURCE_DB", "wildlife"),
            connect_timeout = 30,
            read_timeout    = 60,
            write_timeout   = 60,
            cursorclass     = cursor_class,
        )
        ok(f"Connected to source: {os.getenv('SOURCE_HOST')} / {os.getenv('SOURCE_DB')}")
        return conn
    except Exception as e:
        err(f"Source connection failed: {e}")
        raise


def get_dest_connection():
    """Connect to PostgreSQL destination."""
    info("Connecting to PostgreSQL destination…")
    try:
        conn = psycopg2.connect(
            host     = os.getenv("DEST_HOST"),
            port     = int(os.getenv("DEST_PORT", 5432)),
            user     = os.getenv("DEST_USER"),
            password = os.getenv("DEST_PASS"),
            dbname   = os.getenv("DEST_DB", "postgres"),
            connect_timeout = 15,
        )
        conn.autocommit = False
        ok(f"Connected to destination: {os.getenv('DEST_HOST')} / {os.getenv('DEST_DB')}")
        return conn
    except Exception as e:
        err(f"Destination connection failed: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# 2. SCHEMA INTROSPECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_source_columns(conn, table: str) -> set:
    """Return the set of column names that actually exist in a MariaDB table."""
    with conn.cursor() as cur:
        cur.execute(f"SHOW COLUMNS FROM `{table}`;")
        rows = cur.fetchall()
    return {r["Field"] for r in rows}


def get_source_tables(conn) -> set:
    """Return all table names in the source database."""
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES;")
        rows = cur.fetchall()
    return {list(r.values())[0] for r in rows}


def introspect_source(conn):
    """
    Inspect the live wildlife schema and map each source table's columns.
    Returns a dict: { table_name: set_of_columns }
    """
    info("Introspecting source schema…")
    tables = get_source_tables(conn)

    target_tables = {
        "applications", "application_statuses", "application_histories",
        "application_types", "vouchers", "fees_",
    }
    found    = target_tables & tables
    missing  = target_tables - tables

    if missing:
        warn(f"Tables not found in source (will skip JOINs): {missing}")

    schema = {}
    for tbl in found:
        cols = get_source_columns(conn, tbl)
        schema[tbl] = cols
        ok(f"  {tbl}: {len(cols)} columns")

    return schema, found, missing


# ─────────────────────────────────────────────────────────────────────────────
# 3. EXTRACTION QUERY  (built dynamically based on introspection)
# ─────────────────────────────────────────────────────────────────────────────

def build_extraction_query(schema: dict, found_tables: set,
                           incremental: bool = False,
                           watermark: str = None) -> str:
    """
    Builds a denormalizing SQL query that maps the live wildlife schema to the
    hunting_denormal column layout using the real column names discovered
    from the MariaDB replica.

    Mapping decisions (based on live introspection):
      - age                   → applicant_dob  (no dedicated age column)
      - gender                → applicant_gender_id
      - application_start_date→ applications.created_at
      - district_id           → permanent_district_id
      - district_title        → NOT present; pulled from district lookup if available
      - citizen_id            → applicant_cnic
      - profession_id / title → NOT present in applications; NULL substituted
      - qualification         → NOT present; NULL substituted
      - status_id             → applications.application_status  (FK into application_statuses)
      - status_title          → application_statuses.title  (lookup join)
      - status_created_date   → latest application_histories.created_at for this app
      - status_update_date    → latest application_histories.updated_at for this app
      - total_amount          → vouchers.total_amount
      - payment_date          → vouchers.payment_date
      - voucher_payment_status→ vouchers.voucher_payment_status
    """

    def col(table, column, alias=None):
        """Return `table`.`column` if it exists in the live schema, else NULL AS alias."""
        alias = alias or column
        if table in found_tables and column in schema.get(table, set()):
            return f"`{table}`.`{column}` AS `{alias}`"
        else:
            warn(f"  Column `{table}`.`{column}` not found → substituting NULL AS {alias}")
            return f"NULL AS `{alias}`"

    # ── Application-level columns (using real column names from live schema) ──
    app_cols = [
        col("applications", "id",                       "application_id"),
        col("applications", "user_id"),
        col("applications", "application_type_id"),
        # 'age' not in schema → use DOB as proxy
        col("applications", "applicant_dob",            "age"),
        col("applications", "permanent_address"),
        # 'gender' not in schema → use gender_id
        col("applications", "applicant_gender_id",      "gender"),
        col("applications", "created_at",               "application_start_date"),
        col("applications", "updated_at",               "application_last_updated"),
        # district_id → permanent_district_id
        col("applications", "permanent_district_id",    "district_id"),
        # district_title not available in source; NULL placeholder
        "NULL AS `district_title`",
        # citizen_id → CNIC
        col("applications", "applicant_cnic",           "citizen_id"),
        # profession columns not in source schema
        "NULL AS `profession_id`",
        "NULL AS `profession_title`",
        "NULL AS `qualification`",
    ]

    # ── Status columns ────────────────────────────────────────────────────────
    # application_statuses is a LOOKUP table joined via applications.application_status
    # application_histories is the TRANSACTION log with timestamps per status change
    status_cols = [
        col("applications",         "application_status",   "status_id"),
        col("application_statuses", "title",                "status_title"),
        col("application_histories","created_at",           "status_created_date"),
        col("application_histories","updated_at",           "status_update_date"),
    ]

    # ── Payment / voucher columns (exact column names in vouchers table) ──────
    voucher_cols = [
        col("vouchers", "total_amount"),
        col("vouchers", "payment_date"),
        col("vouchers", "voucher_payment_status"),
    ]

    select_clause = ",\n    ".join(app_cols + status_cols + voucher_cols)

    # ── JOINs ─────────────────────────────────────────────────────────────────
    joins = []

    # application_statuses is a config/lookup table; join on applications.application_status = id
    if "application_statuses" in found_tables:
        joins.append("""
    LEFT JOIN `application_statuses`
        ON `application_statuses`.`id` = `applications`.`application_status`""")

    # application_histories: get the LATEST history row per application
    if "application_histories" in found_tables:
        joins.append("""
    LEFT JOIN `application_histories`
        ON `application_histories`.`application_id` = `applications`.`id`
        AND `application_histories`.`id` = (
            SELECT MAX(`_ah`.`id`)
            FROM `application_histories` AS `_ah`
            WHERE `_ah`.`application_id` = `applications`.`id`
        )""")

    # vouchers: get the LATEST voucher per application
    if "vouchers" in found_tables:
        joins.append("""
    LEFT JOIN `vouchers`
        ON `vouchers`.`application_id` = `applications`.`id`
        AND `vouchers`.`id` = (
            SELECT MAX(`_v`.`id`)
            FROM `vouchers` AS `_v`
            WHERE `_v`.`application_id` = `applications`.`id`
        )""")

    join_clause = "".join(joins)

    # ── Incremental filter ────────────────────────────────────────────────────
    where_clause = ""
    if incremental and watermark:
        if "applications" in found_tables and "updated_at" in schema.get("applications", set()):
            where_clause = f"\nWHERE `applications`.`updated_at` > '{watermark}'"
            info(f"Incremental mode — watermark: {watermark}")
        else:
            warn("Incremental mode requested but `applications`.`updated_at` not found. Running full load.")

    query = f"""
SELECT
    {select_clause}
FROM `applications`{join_clause}{where_clause}
ORDER BY `applications`.`id`
"""
    return query


# ─────────────────────────────────────────────────────────────────────────────
# 4. WATERMARK  (for incremental loads)
# ─────────────────────────────────────────────────────────────────────────────

def read_watermark() -> str | None:
    if os.path.exists(WATERMARK_FILE):
        with open(WATERMARK_FILE) as f:
            return f.read().strip()
    return None


def write_watermark(ts: str):
    with open(WATERMARK_FILE, "w") as f:
        f.write(ts)
    ok(f"Watermark updated → {ts}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. DESTINATION — UPSERT
# ─────────────────────────────────────────────────────────────────────────────

# All columns in hunting_denormal (must match PG table exactly)
DEST_COLUMNS = [
    "application_id", "user_id", "application_type_id", "age",
    "permanent_address", "gender", "application_start_date",
    "application_last_updated", "status_id", "status_title",
    "status_created_date", "status_update_date", "district_id",
    "district_title", "citizen_id", "profession_id", "profession_title",
    "qualification", "total_amount", "payment_date", "voucher_payment_status",
]

UPDATE_COLUMNS = [c for c in DEST_COLUMNS if c != "application_id"]

DEST_TABLE  = os.getenv("DEST_TABLE",  "hunting_denormal")
DEST_SCHEMA = os.getenv("DEST_SCHEMA", "public")

UPSERT_SQL = f"""
INSERT INTO {DEST_SCHEMA}.{DEST_TABLE}
    ({", ".join(DEST_COLUMNS)})
VALUES %s
ON CONFLICT (application_id) DO UPDATE SET
    {", ".join(f"{c} = EXCLUDED.{c}" for c in UPDATE_COLUMNS)}
"""


def get_dest_row_count(dest_conn) -> int:
    with dest_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {DEST_SCHEMA}.{DEST_TABLE};")
        return cur.fetchone()[0]


def df_to_tuples(df: pd.DataFrame) -> list:
    """
    Convert the extracted DataFrame into a list of tuples ordered exactly
    by DEST_COLUMNS.  Missing columns are filled with None; NaN → None.
    Using reindex + where is far more reliable than row-by-row .get().
    """
    # Align DataFrame columns to destination order; fill any gaps with None
    df_aligned = df.reindex(columns=DEST_COLUMNS)
    # Replace every NaN/NaT with Python None for psycopg2 compatibility
    df_aligned = df_aligned.where(pd.notna(df_aligned), other=None)
    return [tuple(row) for row in df_aligned.itertuples(index=False, name=None)]


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run(incremental: bool = False, dry_run: bool = False):
    banner("Wildlife → hunting_denormal Pipeline")
    info(f"Mode: {'INCREMENTAL' if incremental else 'FULL LOAD'}"
         + (" | DRY RUN (no writes)" if dry_run else ""))

    src_conn  = None
    dest_conn = None

    # ── Error log ──────────────────────────────────────────────────────────
    error_log_path = "wildlife_pipeline_errors.log"
    error_log      = open(error_log_path, "w")

    stats = {"extracted": 0, "loaded": 0, "skipped": 0, "failed": 0}

    try:
        # ── Step 1: Connect ────────────────────────────────────────────────
        banner("Step 1 / 5 — Connecting to Databases")
        # DictCursor connection → schema introspection (SHOW TABLES / SHOW COLUMNS)
        src_conn       = get_source_connection(dict_cursor=True)
        # Plain-cursor connection → pd.read_sql extraction (avoids key-iteration bug)
        src_conn_plain = get_source_connection(dict_cursor=False)
        if not dry_run:
            dest_conn = get_dest_connection()

        # ── Step 2: Introspect schema ──────────────────────────────────────
        banner("Step 2 / 5 — Introspecting Source Schema")
        schema, found_tables, missing_tables = introspect_source(src_conn)

        # ── Step 3: Build & run extraction query ───────────────────────────
        banner("Step 3 / 5 — Extracting Data from MariaDB")
        watermark = read_watermark() if incremental else None
        query     = build_extraction_query(schema, found_tables, incremental, watermark)

        info("Running extraction query…")
        # Use plain-cursor connection so pd.read_sql receives tuple rows,
        # not dict rows (iterating a dict yields keys = column names, not values)
        df = pd.read_sql(query, src_conn_plain)
        stats["extracted"] = len(df)
        ok(f"Extracted {len(df):,} rows from source.")

        if df.empty:
            warn("No data returned from source. Nothing to load.")
            return

        # Get source count for reconciliation
        with src_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM `applications`;")
            total_apps = cur.fetchone()["cnt"]
        info(f"Total applications in source: {total_apps:,}")

        # ── Step 4: Load into PostgreSQL ───────────────────────────────────
        banner("Step 4 / 5 — Loading into PostgreSQL (hunting_denormal)")

        if dry_run:
            warn("DRY RUN — skipping database writes.")
            warn(f"Would have loaded {len(df):,} rows into {DEST_SCHEMA}.{DEST_TABLE}.")
        else:
            dest_count_before = get_dest_row_count(dest_conn)
            info(f"Destination rows before load: {dest_count_before:,}")

            # ── Pre-convert all rows to tuples (reindex → None-fill → tuples) ──
            info(f"DataFrame columns (first 5): {df.columns.tolist()[:5]}")
            all_tuples    = df_to_tuples(df)
            info(f"Sample tuple[0]: {all_tuples[0]}")

            # Explicit per-value template so execute_values never guesses
            pg_template   = "(" + ", ".join(["%s"] * len(DEST_COLUMNS)) + ")"

            batches       = [all_tuples[i:i + BATCH_SIZE]
                             for i in range(0, len(all_tuples), BATCH_SIZE)]
            total_batches = len(batches)

            print()  # blank line before progress bar
            pbar = tqdm(
                total         = len(all_tuples),
                desc          = "  Loading rows",
                unit          = "rows",
                bar_format    = "{l_bar}{bar:40}{r_bar}",
                colour        = "green",
                file          = sys.stdout,
                dynamic_ncols = True,
            )

            with dest_conn.cursor() as cur:
                for batch_num, batch in enumerate(batches, start=1):
                    try:
                        psycopg2.extras.execute_values(
                            cur, UPSERT_SQL, batch,
                            template=pg_template, page_size=BATCH_SIZE
                        )
                        dest_conn.commit()
                        stats["loaded"] += len(batch)
                        pbar.set_postfix({
                            "batch": f"{batch_num}/{total_batches}",
                            "loaded": f"{stats['loaded']:,}",
                            "failed": stats["failed"],
                        })
                        pbar.update(len(batch))

                    except Exception as batch_err:
                        dest_conn.rollback()
                        stats["failed"] += len(batch)
                        err_msg = (
                            f"Batch {batch_num} FAILED "
                            f"(app_ids {batch[0][0]}–{batch[-1][0]}): {batch_err}"
                        )
                        err(err_msg)
                        error_log.write(err_msg + "\n")
                        pbar.update(len(batch))

            pbar.close()
            print()  # blank line after progress bar

            dest_count_after = get_dest_row_count(dest_conn)
            ok(f"Destination rows after load: {dest_count_after:,}")

        # ── Step 5: Reconciliation report ──────────────────────────────────
        banner("Step 5 / 5 — Reconciliation Report")

        if not dry_run:
            diff = stats["extracted"] - stats["loaded"] - stats["failed"]
            stats["skipped"] = max(0, diff)

            print(f"""
  {'─'*45}
  {'Metric':<30} {'Count':>10}
  {'─'*45}
  {'Rows extracted from source':<30} {stats['extracted']:>10,}
  {'Rows loaded to destination':<30} {stats['loaded']:>10,}
  {'Rows skipped (0 delta)':<30} {stats['skipped']:>10,}
  {'Rows failed':<30} {stats['failed']:>10,}
  {'─'*45}
  {'Destination BEFORE load':<30} {dest_count_before:>10,}
  {'Destination AFTER load':<30} {dest_count_after:>10,}
  {'Net new rows':<30} {dest_count_after - dest_count_before:>10,}
  {'─'*45}
""")
            if stats["failed"] > 0:
                warn(f"{stats['failed']} rows failed. See: {error_log_path}")
            else:
                ok("All rows loaded successfully. No errors.")

            # Save watermark for next incremental run
            if incremental:
                ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                write_watermark(ts)

        if not dry_run and stats["loaded"] > 0:
            banner("Pipeline Completed Successfully ✔")
        elif dry_run:
            banner("Dry Run Completed ✔ (no data written)")
        else:
            banner("Pipeline Finished with Errors ✘")

    except KeyboardInterrupt:
        warn("Pipeline interrupted by user.")
        if dest_conn:
            dest_conn.rollback()

    except Exception as e:
        err(f"Pipeline failed with exception: {e}")
        traceback.print_exc()
        if dest_conn:
            dest_conn.rollback()
        sys.exit(1)

    finally:
        error_log.close()
        if src_conn:
            src_conn.close()
        if 'src_conn_plain' in dir() and src_conn_plain:
            src_conn_plain.close()
        if dest_conn:
            dest_conn.close()
        info("All connections closed.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wildlife → hunting_denormal ETL Pipeline"
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="Only extract records updated since the last run (uses watermark file).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Extract data from source but do NOT write to destination.",
    )
    args = parser.parse_args()
    run(incremental=args.incremental, dry_run=args.dry_run)
