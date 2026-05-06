import sqlite3
import os

db_paths = ['instance/millet.db']
for db_file in db_paths:
    if os.path.exists(db_file):
        print(f"Patching {db_file} for sensor_data...")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        columns_to_add = [
            ("soil_moisture_raw", "INTEGER"),
            ("soil_moisture_percent", "FLOAT"),
        ]
        
        try:
            existing_cols = [info[1] for info in cursor.execute("PRAGMA table_info(sensor_data)").fetchall()]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_cols:
                    print(f"Adding {col_name} to sensor_data...")
                    try:
                        cursor.execute(f"ALTER TABLE sensor_data ADD COLUMN {col_name} {col_type};")
                        conn.commit()
                    except Exception as e:
                        print(f"Error adding {col_name}: {e}")
            print("Done patching.")
        except Exception as e:
            print("Error:", e)
        conn.close()
