import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

hosts_to_try = [
    os.getenv("SOURCE_HOST", "172.16.104.199"),
    "172.16.104.197"
]

user = os.getenv("SOURCE_USER", "hamzaDAProdReplica")
password = os.getenv("SOURCE_PASS", "hamzaDAProd@ReplicaSupSet")
database = os.getenv("SOURCE_DB", "wildlife")
port = int(os.getenv("SOURCE_PORT", 3306))

for host in dict.fromkeys(hosts_to_try):
    print(f"\n--- Testing MariaDB host: {host}:{port} ---")
    try:
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=5,
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✔ SUCCESS: Connected to MariaDB on {host}!")
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            tables = cursor.fetchall()
            print(f"Database '{database}' has {len(tables)} tables:")
            for t in tables[:10]:
                print(" -", list(t.values())[0])
        connection.close()
        break
    except Exception as e:
        print(f"✘ Connection to {host} failed: {e}")
