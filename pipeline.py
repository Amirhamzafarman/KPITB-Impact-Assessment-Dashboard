import os
import sys
import logging
import datetime
import pymysql
import pandas as pd
from dotenv import load_dotenv
import paramiko

# Load configurations from .env file
load_dotenv()

# Setup logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_source_connection():
    """Establishes a secure connection to the source MySQL replica database."""
    logging.info("Connecting to source MySQL database replica...")
    try:
        connection = pymysql.connect(
            host=os.getenv("SOURCE_HOST"),
            port=int(os.getenv("SOURCE_PORT", 3306)),
            user=os.getenv("SOURCE_USER"),
            password=os.getenv("SOURCE_PASS"),
            database=os.getenv("SOURCE_DB"),
            connect_timeout=15,
            cursorclass=pymysql.cursors.DictCursor
        )
        logging.info("✔ Connected to source database successfully.")
        return connection
    except Exception as e:
        logging.error(f"❌ Failed to connect to source database: {e}")
        raise

def explore_schema(connection):
    """Explores the database schema and lists all tables related to arms and licensing."""
    logging.info("Exploring database schema for licensing tables...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            all_tables = [list(t.values())[0] for t in tables]
            
            # Filter tables related to arms or licensing
            relevant_tables = [t for t in all_tables if 'license' in t.lower() or 'arms' in t.lower()]
            logging.info(f"Found {len(all_tables)} total tables. Relevant tables: {relevant_tables}")
            return relevant_tables
    except Exception as e:
        logging.error(f"❌ Schema exploration failed: {e}")
        return []

def extract_and_aggregate(connection, db_table):
    """
    Extracts raw arms & licensing records, performs SQL-level aggregation, 
    and returns a Pandas DataFrame.
    """
    logging.info(f"Extracting and aggregating data from table '{db_table}'...")
    
    # Generic aggregation query (update column names based on actual schema)
    query = f"""
    SELECT 
        district_name,
        license_type,
        status,
        COUNT(*) AS total_licenses,
        SUM(licensing_fee) AS total_fees_collected,
        AVG(DATEDIFF(issued_date, applied_date)) AS avg_processing_days,
        CURRENT_DATE() AS report_date
    FROM 
        {db_table}
    GROUP BY 
        district_name, license_type, status;
    """
    
    try:
        # Pull data directly using pandas
        df = pd.read_sql(query, connection)
        logging.info(f"✔ Aggregation successful. Retrieved {len(df)} rows.")
        return df
    except Exception as e:
        logging.error(f"❌ Aggregation query failed: {e}")
        logging.info("Attempting simplified aggregation without date differences...")
        
        # Fallback simplified query
        fallback_query = f"""
        SELECT 
            district_name,
            license_type,
            status,
            COUNT(*) AS total_licenses,
            SUM(licensing_fee) AS total_fees_collected
        FROM 
            {db_table}
        GROUP BY 
            district_name, license_type, status;
        """
        try:
            df = pd.read_sql(fallback_query, connection)
            logging.info(f"✔ Fallback aggregation successful. Retrieved {len(df)} rows.")
            return df
        except Exception as err:
            logging.error(f"❌ Fallback aggregation also failed: {err}")
            raise

def export_to_staging(df, filename="staging_licensing_data.csv"):
    """Saves the aggregated DataFrame locally to a CSV file."""
    os.makedirs("./staging", exist_ok=True)
    file_path = os.path.join("./staging", filename)
    try:
        df.to_csv(file_path, index=False)
        logging.info(f"✔ Aggregated data exported to local staging: {file_path}")
        return file_path
    except Exception as e:
        logging.error(f"❌ Failed to export staging file: {e}")
        raise

def upload_via_sftp(local_file_path):
    """
    Transfers the staging file to the destination server using SSH/SFTP.
    Use this if the destination is a file server landing zone.
    """
    host = os.getenv("DEST_HOST")
    port = int(os.getenv("DEST_PORT", 22))
    username = os.getenv("DEST_USER")
    password = os.getenv("DEST_PASS")
    
    logging.info(f"Attempting SFTP transfer to {username}@{host}:{port}...")
    try:
        transport = paramiko.Transport((host, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        remote_filename = os.path.basename(local_file_path)
        remote_path = f"/var/data/staging/{remote_filename}"  # Adjust to remote path
        
        logging.info(f"Uploading {local_file_path} to remote destination: {remote_path}...")
        sftp.put(local_file_path, remote_path)
        
        sftp.close()
        transport.close()
        logging.info("✔ SFTP upload complete.")
        return True
    except Exception as e:
        logging.error(f"❌ SFTP upload failed: {e}")
        return False

def upload_to_destination_db(df):
    """
    Ingests the aggregated DataFrame directly into the destination database.
    Use this if the destination is a MySQL or PostgreSQL database.
    """
    host = os.getenv("DEST_HOST")
    port = int(os.getenv("DEST_PORT", 3306))
    username = os.getenv("DEST_USER")
    password = os.getenv("DEST_PASS")
    db_name = os.getenv("DEST_DB")
    
    logging.info(f"Attempting direct database load to target database {db_name} on {host}...")
    try:
        # Connect to destination database
        dest_conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=db_name,
            connect_timeout=10
        )
        
        # Load rows
        with dest_conn.cursor() as cursor:
            # Create staging table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS staging_arms_aggregates (
                    district_name VARCHAR(100),
                    license_type VARCHAR(100),
                    status VARCHAR(50),
                    total_licenses INT,
                    total_fees_collected DECIMAL(15,2),
                    avg_processing_days DECIMAL(5,2),
                    report_date DATE,
                    PRIMARY KEY (district_name, license_type, status)
                );
            """)
            
            # Upsert records
            for _, row in df.iterrows():
                sql = """
                    INSERT INTO staging_arms_aggregates 
                    (district_name, license_type, status, total_licenses, total_fees_collected, avg_processing_days, report_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                        total_licenses = VALUES(total_licenses),
                        total_fees_collected = VALUES(total_fees_collected),
                        avg_processing_days = VALUES(avg_processing_days),
                        report_date = VALUES(report_date);
                """
                cursor.execute(sql, (
                    row.get('district_name'),
                    row.get('license_type'),
                    row.get('status'),
                    int(row.get('total_licenses', 0)),
                    float(row.get('total_fees_collected', 0.0)) if row.get('total_fees_collected') else 0.0,
                    float(row.get('avg_processing_days', 0.0)) if row.get('avg_processing_days') else 0.0,
                    row.get('report_date')
                ))
            
            dest_conn.commit()
        dest_conn.close()
        logging.info("✔ Direct destination database load complete.")
        return True
    except Exception as e:
        logging.error(f"❌ Direct database load failed: {e}")
        return False

def run():
    logging.info("=== Starting RTS Arms & Licensing Pipeline ===")
    source_conn = None
    try:
        # Step 1: Connect to source database
        source_conn = get_source_connection()
        
        # Step 2: Explore tables
        tables = explore_schema(source_conn)
        
        if not tables:
            logging.warning("No arms or licensing tables found. Please specify database/table manually.")
            # Default table fallback
            target_table = "arms_licenses"
        else:
            target_table = tables[0]
            logging.info(f"Selected table for aggregation: {target_table}")
            
        # Step 3: Extract and Aggregate
        df = extract_and_aggregate(source_conn, target_table)
        
        # Step 4: Save Staging File locally
        staging_file = export_to_staging(df)
        
        # Step 5: Transfer / Ingest (try direct DB or fallback to SFTP)
        # Note: Change the logic below based on your actual target server type
        success = upload_to_destination_db(df)
        if not success:
            logging.info("Direct database ingestion unsuccessful or not configured. Trying SFTP upload...")
            success = upload_via_sftp(staging_file)
            
        if success:
            logging.info("=== Pipeline Completed Successfully ===")
        else:
            logging.error("=== Pipeline Finished with Errors ===")
            
    except Exception as e:
        logging.error(f"=== Pipeline Failed: {e} ===")
    finally:
        if source_conn:
            source_conn.close()

if __name__ == "__main__":
    run()
