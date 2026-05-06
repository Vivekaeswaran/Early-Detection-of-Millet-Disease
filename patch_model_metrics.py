"""
patch_model_metrics.py
======================
Safe one-time migration script.
Adds missing columns to the existing `model_metrics` table in the SQLite DB.

Run once:
    python patch_model_metrics.py

Safe to re-run: each ALTER TABLE is wrapped in try/except so it skips
columns that already exist.
"""

import sqlite3
import os

# Resolve absolute path to the database used by Flask
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "millet.db")

if not os.path.exists(DB_PATH):
    print(f"[ERROR] Database not found at: {DB_PATH}")
    print("  Make sure you have run the Flask app at least once to create the DB.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Columns to add safely ────────────────────────────────────────────────────
NEW_COLUMNS = [
    ("training_accuracy",   "REAL"),
    ("validation_accuracy", "REAL"),
    ("validation_loss",     "REAL"),
]

print(f"[INFO] Patching table 'model_metrics' in: {DB_PATH}\n")

# First — ensure the table exists (harmless if it already does)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_metrics (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name         TEXT,
        accuracy           REAL,
        loss               REAL,
        training_accuracy  REAL,
        validation_accuracy REAL,
        validation_loss    REAL,
        trained_at         DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()
print("[OK] Ensured model_metrics table exists.")

for col_name, col_type in NEW_COLUMNS:
    try:
        cursor.execute(f"ALTER TABLE model_metrics ADD COLUMN {col_name} {col_type}")
        conn.commit()
        print(f"[ADDED]   Column '{col_name}' ({col_type})")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"[EXISTS]  Column '{col_name}' already present — skipped.")
        else:
            print(f"[ERROR]   {col_name}: {e}")

conn.close()
print("\n[DONE] patch_model_metrics.py completed successfully.")
print("       You can now run: python train_model.py --force")
