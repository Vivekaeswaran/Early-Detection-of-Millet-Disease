import sqlite3
import os

db_paths = ['instance/millet.db']
for db_file in db_paths:
    if os.path.exists(db_file):
        print(f"Patching {db_file}...")
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # ExpertAdvice columns that were added but not in DB
        columns_to_add = [
            ("disease_name", "VARCHAR(100)"),
            ("symptoms", "TEXT"),
            ("treatment", "TEXT"),
            ("fertilizer_suggestion", "TEXT"),
            ("prevention_methods", "TEXT"),
        ]
        
        existing_cols = [info[1] for info in cursor.execute("PRAGMA table_info(expert_advice)").fetchall()]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_cols:
                print(f"Adding {col_name} to expert_advice...")
                try:
                    cursor.execute(f"ALTER TABLE expert_advice ADD COLUMN {col_name} {col_type};")
                    conn.commit()
                except Exception as e:
                    print(f"Error adding {col_name}: {e}")
        
        print("Done patching.")
        conn.close()
