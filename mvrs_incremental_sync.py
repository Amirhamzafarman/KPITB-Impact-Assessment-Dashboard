import argparse
import csv
import datetime as dt
import io
import os
import random
import sys
import time

import mysql.connector
import psycopg2
from sshtunnel import SSHTunnelForwarder

# SSH Tunnel Configuration
SSH_HOST = '172.16.104.199'
SSH_PORT = 22
SSH_USER = 'hamzada'
SSH_PASSWORD = 'hamzaDAProd@ReplicaSupSet'

# Source MySQL Configuration
SOURCE_HOST = '172.16.104.199'
SOURCE_USER = 'hamzaDAProdReplica'
SOURCE_PASSWORD = 'hamzaDAProd@ReplicaSupSet'
SOURCE_DB = 'mvrs_v2'

# Destination PostgreSQL Configuration
DEST_HOST = '175.107.59.192'
DEST_PORT = 443
DEST_USER = 'hamza'
DEST_PASSWORD = 'hcBgR8Rhg329tdO4ClZj!#'
DEST_DB = 'postgres'
DEST_SCHEMA = 'public'
DEST_TABLE = 'MVRS'

BATCH_SIZE = 20000

# Source query without inaccessible sd_portal schema tables
SOURCE_QUERY = """
SELECT
    a.id AS application_id,
    a.user_id,
    a.service_id,
    a.service_type_id,

    CASE WHEN a.cnic = o.cnic THEN a.applicant_name ELSE o.applicant_name END AS applicant_name,
    CASE WHEN a.cnic = o.cnic THEN a.father_name ELSE o.father_name END AS father_name,
    CASE WHEN a.cnic = o.cnic THEN a.cnic ELSE o.cnic END AS cnic,
    CASE WHEN a.cnic = o.cnic THEN a.contact ELSE o.contact END AS applicant_contact,
    CASE WHEN a.cnic = o.cnic THEN a.gender_id ELSE o.gender_id END AS gender_id,
    CASE WHEN a.cnic = o.cnic THEN a.current_address ELSE o.current_address END AS current_address,
    CASE WHEN a.cnic = o.cnic THEN DATE(a.dob) ELSE DATE(o.dob) END AS dob,

    TIMESTAMPDIFF(
        YEAR,
        CASE WHEN a.cnic = o.cnic THEN a.dob ELSE o.dob END,
        CURDATE()
    ) AS age,

    CASE WHEN a.cnic = o.cnic THEN a.permanent_address ELSE o.permanent_address END AS permanent_address,

    CASE 
        WHEN (CASE WHEN a.cnic = o.cnic THEN a.gender_id ELSE o.gender_id END) = 1 THEN 'Male'
        WHEN (CASE WHEN a.cnic = o.cnic THEN a.gender_id ELSE o.gender_id END) = 2 THEN 'Female'
        WHEN (CASE WHEN a.cnic = o.cnic THEN a.gender_id ELSE o.gender_id END) = 3 THEN 'Transgender'
        ELSE NULL
    END AS gender,

    DATE(a.created_at) AS application_start_date,
    DATE(ah.updated_at) AS application_last_updated,

    s.id as service_master_id,
    s.title as service_name,

    st.id AS status_id,
    st.title AS status_title,
    DATE(ah.created_at) AS status_created_date,
    DATE(ah.updated_at) AS status_update_date,
    DATEDIFF(DATE(ahl.updated_at), DATE(ah.created_at)) AS days,

    ah.to_department_id,
    ah.to_department_title,

    d.district_id,
    d.title AS district_title,

    NULL AS citizen_id,
    NULL AS profession_id,

    NULL AS profession_title,
    NULL AS qualification,

    v.total_amount,
    v.payment_date,
    v.voucher_payment_status,
    v.payment_mode,
    v.payment_nature

FROM applications a

INNER JOIN application_history_latest ahl
    ON a.id = ahl.application_id

LEFT JOIN application_histories ah
    ON a.id = ah.application_id

INNER JOIN vouchers v
    ON a.id = v.application_id

LEFT JOIN owners o
    ON a.vehicle_id = o.vehicle_id
   AND o.is_current IN (1,2)

LEFT JOIN services s
    ON a.service_id = s.id

LEFT JOIN statuses st
    ON st.id = ah.status_id

LEFT JOIN districts d
    ON a.district_id = d.district_id

WHERE v.payment_date IS NOT NULL
  AND v.voucher_payment_status = 'paid'
"""


def log(message):
    print(message, flush=True)


def quote_ident(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def pg_table_name():
    return f"{quote_ident(DEST_SCHEMA)}.{quote_ident(DEST_TABLE)}"


def deduplicate_columns(columns):
    """Handle duplicate column names by appending _2, _3, etc."""
    seen = {}
    result = []
    for col in columns:
        if col in seen:
            seen[col] += 1
            result.append(f"{col}_{seen[col]}")
        else:
            seen[col] = 1
            result.append(col)
    return result


def normalize_value(value):
    if value is None:
        return r'\N'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, dt.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, dt.date):
        return value.strftime('%Y-%m-%d')
    return str(value)


def open_ssh_tunnel(max_retries: int = 3):
    """Establish an SSH tunnel to the MySQL host."""
    for attempt in range(1, max_retries + 1):
        try:
            log(f"Opening SSH Tunnel to {SSH_USER}@{SSH_HOST}:{SSH_PORT}...")
            tunnel = SSHTunnelForwarder(
                (SSH_HOST, SSH_PORT),
                ssh_username=SSH_USER,
                ssh_password=SSH_PASSWORD,
                remote_bind_address=('127.0.0.1', 3306),
                set_keepalive=15.0
            )
            tunnel.start()
            log(f"✔ SSH Tunnel active on local port {tunnel.local_bind_port}")
            return tunnel
        except Exception as e:
            log(f"SSH Tunnel attempt {attempt}/{max_retries} failed: {e}")
            if attempt == max_retries:
                raise
            time.sleep(2)


def connect_mysql(local_port: int, retries: int = 5, backoff: float = 1.0):
    """Establish a MySQL connection through the SSH tunnel with exponential backoff."""
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
            return conn
        except mysql.connector.Error as e:
            attempt += 1
            if attempt > retries:
                log(f"Failed to connect to MySQL after {retries} attempts: {e}")
                raise
            wait = backoff * (2 ** (attempt - 1)) + random.random()
            log(f"MySQL connection error ({e}); retrying in {wait:.1f}s (attempt {attempt}/{retries})")
            time.sleep(wait)


def print_progress_bar(iteration, total, start_time, prefix='', suffix='', decimals=1, length=40, fill='#', print_end="\r"):
    elapsed_time = time.time() - start_time
    if iteration <= 0:
        speed = 0.0
        eta = 0.0
    else:
        speed = iteration / elapsed_time
        eta = (total - iteration) / speed if speed > 0 else 0.0

    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total))) if total > 0 else "100.0"
    filled_length = int(length * iteration // total) if total > 0 else length
    bar = fill * filled_length + '-' * (length - filled_length)
    
    speed_fmt = f"{speed:,.0f} rows/s" if speed >= 1 else f"{speed:.2f} rows/s"
    
    if eta >= 3600:
        eta_fmt = f"{int(eta // 3600)}h {int((eta % 3600) // 60)}m"
    elif eta >= 60:
        eta_fmt = f"{int(eta // 60)}m {int(eta % 60)}s"
    else:
        eta_fmt = f"{int(eta)}s"
        
    full_suffix = f"{suffix} ({speed_fmt}, ETA: {eta_fmt})" if iteration < total else f"{suffix} (Done in {elapsed_time:.1f}s)"
    
    try:
        sys.stdout.write(f'\r{prefix} |{bar}| {percent}% {full_suffix}')
        sys.stdout.flush()
    except UnicodeEncodeError:
        safe_bar = '#' * filled_length + '-' * (length - filled_length)
        sys.stdout.write(f'\r{prefix} |{safe_bar}| {percent}% {full_suffix}')
        sys.stdout.flush()
        
    if iteration >= total and total > 0:
        sys.stdout.write('\n')
        sys.stdout.flush()


def wrapped_source_query(limit=None, min_id=None):
    base_query = SOURCE_QUERY.strip().rstrip(';')
    if min_id is not None:
        base_query += f"\n  AND a.id > {min_id}"  # Note: > instead of >= for incremental
    base_query += "\nORDER BY a.id"
    wrapped = f"SELECT * FROM ({base_query}) AS src"
    if limit is not None:
        wrapped += f" LIMIT {int(limit)}"
    return wrapped


def stream_data(mysql_conn, pg_conn, min_id, total_rows, tunnel_port):
    if total_rows == 0:
        return 0

    mysql_cursor = mysql_conn.cursor()
    pg_cursor = pg_conn.cursor()

    mysql_cursor.execute(wrapped_source_query(limit=1, min_id=min_id))
    columns = deduplicate_columns([desc[0] for desc in mysql_cursor.description])
    mysql_cursor.fetchall()  # Consume unread result
    
    mysql_cursor.execute(wrapped_source_query(min_id=min_id))

    copy_sql = (
        f"COPY {pg_table_name()} ({', '.join(quote_ident(column) for column in columns)}) "
        "FROM STDIN WITH (FORMAT text, DELIMITER E'\\t', NULL '\\\\N')"
    )

    rows_inserted = 0
    batch_no = 0
    start_time = time.time()
    last_id = None

    print_progress_bar(0, total_rows, start_time, prefix='Progress:', suffix='Starting...', length=40)

    while True:
        try:
            rows = mysql_cursor.fetchmany(BATCH_SIZE)
        except mysql.connector.Error as e:
            log(f"\nMySQL fetch error: {e}. Reconnecting and retrying batch.")
            try:
                mysql_cursor.close()
                mysql_conn.close()
            except Exception:
                pass
            
            mysql_conn = connect_mysql(local_port=tunnel_port)
            mysql_cursor = mysql_conn.cursor()
            resume_id = last_id if last_id is not None else min_id
            mysql_cursor.execute(wrapped_source_query(min_id=resume_id))
            rows = mysql_cursor.fetchmany(BATCH_SIZE)

        if not rows:
            break
            
        batch_no += 1
        batch_ids = [row[0] for row in rows]
        if batch_ids:
            last_id = max(batch_ids)
            
        buffer = io.StringIO()
        writer = csv.writer(
            buffer,
            delimiter='\t',
            lineterminator='\n',
            quoting=csv.QUOTE_NONE,
            escapechar='\\',
        )
        for row in rows:
            writer.writerow([normalize_value(value) for value in row])
        buffer.seek(0)
        
        try:
            pg_cursor.copy_expert(copy_sql, buffer)
            pg_conn.commit()
        except psycopg2.errors.UniqueViolation as e:
            log(f"\nDuplicate key error: {e}. Skipping this batch.")
            pg_conn.rollback()
            continue
            
        rows_inserted += len(rows)
        print_progress_bar(rows_inserted, total_rows, start_time, prefix='Progress:', suffix=f'Loaded {rows_inserted:,}/{total_rows:,} rows', length=40)

    mysql_cursor.close()
    pg_cursor.close()
    return rows_inserted


def main():
    parser = argparse.ArgumentParser(description="Incremental sync for MVRS data from MySQL to PostgreSQL.")
    parser.add_argument('-y', '--yes', action='store_true', help="Skip interactive confirmation prompt.")
    args = parser.parse_args()

    log('Connecting to PostgreSQL destination to determine high-water mark...')
    try:
        pg_conn = psycopg2.connect(
            host=DEST_HOST,
            port=DEST_PORT,
            database=DEST_DB,
            user=DEST_USER,
            password=DEST_PASSWORD,
            sslmode='require',
            connect_timeout=300,
        )
    except psycopg2.Error as e:
        log(f"Failed to connect to PostgreSQL: {e}")
        return

    pg_cursor = pg_conn.cursor()
    
    # Verify table exists
    pg_cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        );
    """, (DEST_SCHEMA, DEST_TABLE))
    
    if not pg_cursor.fetchone()[0]:
        log(f"Error: Destination table '{DEST_SCHEMA}.{DEST_TABLE}' does not exist.")
        log("Please run the initial transfer script first.")
        pg_conn.close()
        return

    # Get max application_id
    try:
        pg_cursor.execute(f'SELECT MAX(application_id::bigint) FROM {pg_table_name()}')
        max_id = pg_cursor.fetchone()[0]
    except psycopg2.Error as e:
        log(f"Error reading high-water mark: {e}")
        pg_conn.close()
        return

    if max_id is None:
        log("Destination table is empty. Starting from the beginning (id > 0).")
        max_id = 0
    else:
        log(f"Current high-water mark (MAX application_id): {max_id}")

    pg_cursor.close()

    # Open SSH Tunnel
    tunnel = open_ssh_tunnel()
    
    try:
        log('Connecting to MySQL source via SSH tunnel...')
        mysql_conn = connect_mysql(local_port=tunnel.local_bind_port)
        count_cursor = mysql_conn.cursor()
        
        log('Checking for new records in MySQL...')
        count_query = f"SELECT COUNT(*) FROM ({SOURCE_QUERY.strip().rstrip(';')}\n  AND a.id > {max_id}) AS src"
        count_cursor.execute(count_query)
        total_new_rows = count_cursor.fetchone()[0]
        count_cursor.close()

        if total_new_rows == 0:
            log("No new records found. Sync is already up-to-date.")
            mysql_conn.close()
            pg_conn.close()
            tunnel.stop()
            return

        log(f"\n>>> Found {total_new_rows:,} new record(s) to migrate.")
        
        # Confirmation prompt
        if not args.yes:
            while True:
                choice = input("Do you want to proceed with the incremental sync? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    break
                elif choice in ['n', 'no']:
                    log("Migration cancelled by user.")
                    mysql_conn.close()
                    pg_conn.close()
                    tunnel.stop()
                    return
                else:
                    print("Please enter 'y' or 'n'.")

        log(f'\nStarting data transfer in {BATCH_SIZE:,}-row chunks...')
        rows_inserted = stream_data(mysql_conn, pg_conn, min_id=max_id, total_rows=total_new_rows, tunnel_port=tunnel.local_bind_port)
        log(f'\nIncremental sync complete: {rows_inserted:,} rows inserted.')

        mysql_conn.close()
        pg_conn.close()
    finally:
        tunnel.stop()


if __name__ == '__main__':
    main()
