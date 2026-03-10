import mysql.connector
import sys

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'ram123'
}

try:
    print(f"Connecting with: {db_config}")
    conn = mysql.connector.connect(**db_config)
    print("SUCCESS: MySQL Connected.")
    conn.close()
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
