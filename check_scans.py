import sqlite3
import os

db_path = 'instance/millet.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Latest 10 records from scan_history:")
    cursor.execute("SELECT id, farmer_id, disease_name, confidence, severity, scanned_at FROM scan_history ORDER BY scanned_at DESC LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    conn.close()
else:
    print(f"{db_path} not found.")
