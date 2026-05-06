import sqlite3
import os

db_path = 'instance/millet.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Latest 5 records from sensor_data:")
    cursor.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    conn.close()
else:
    print(f"{db_path} not found.")
