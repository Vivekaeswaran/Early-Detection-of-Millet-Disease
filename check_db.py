import sqlite3
import os

db_path = 'instance/millet.db'
if not os.path.exists(db_path):
    # try root directory if not in instance
    db_path = 'millet.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY created_at DESC LIMIT 5;")
    rows = cursor.fetchall()
    print("SENSOR_DATA ROWS:")
    for row in rows:
        print(row)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
