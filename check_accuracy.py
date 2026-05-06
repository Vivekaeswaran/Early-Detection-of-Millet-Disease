"""
check_accuracy.py  —  One-line command to view model training metrics
=====================================================================
USAGE
-----
    python check_accuracy.py

Reads from (in priority order):
  1. model/training_results.json   (written by train_model.py)
  2. instance/millet.db            (model_metrics table)

No Flask context needed — runs standalone.
"""

import os
import json
import sys

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
RESULTS_JSON = os.path.join(BASE_DIR, "model", "training_results.json")
MODEL_PATH   = os.path.join(BASE_DIR, "model", "millet_disease_model.h5")
DB_PATH      = os.path.join(BASE_DIR, "instance", "millet.db")

SEP  = "=" * 60
SEP2 = "-" * 60


def _from_json():
    """Try to read metrics from training_results.json."""
    if not os.path.exists(RESULTS_JSON):
        return None
    try:
        with open(RESULTS_JSON, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Could not parse training_results.json: {e}")
        return None


def _from_db():
    """Try to read latest row from model_metrics table."""
    if not os.path.exists(DB_PATH):
        return None
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT model_name, training_accuracy, validation_accuracy,
                   loss, validation_loss, trained_at
            FROM model_metrics
            ORDER BY id DESC LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception as e:
        print(f"[WARN] Could not query database: {e}")
    return None


def main():
    print()
    print(SEP)
    print("  MilletGuard AI — Model Accuracy Report")
    print(SEP)

    # ── Check model file exists ───────────────────────────────────────
    if os.path.exists(MODEL_PATH):
        size_mb = os.path.getsize(MODEL_PATH) / (1024 * 1024)
        print(f"  Model File      : millet_disease_model.h5  ({size_mb:.1f} MB)")
        print(f"  Model Status    : ✓ FOUND")
    else:
        print(f"  Model File      : millet_disease_model.h5")
        print(f"  Model Status    : ✗ NOT FOUND — run: python train_model.py")
        print(SEP)
        sys.exit(1)

    print(SEP2)

    # ── Try JSON first, then DB ───────────────────────────────────────
    data = _from_json()
    source = "model/training_results.json"

    if data is None:
        data = _from_db()
        source = "instance/millet.db (model_metrics)"

    if data is None:
        print("  [INFO] No training metrics found.")
        print("         Run:  python train_model.py")
        print("         Then re-run this command.")
        print(SEP)
        sys.exit(0)

    # ── Display metrics ───────────────────────────────────────────────
    model_name   = data.get("model_name", "millet_disease_model.h5")
    train_acc    = data.get("training_accuracy") or data.get("accuracy")
    val_acc      = data.get("validation_accuracy")
    train_loss   = data.get("loss") or data.get("training_loss")
    val_loss     = data.get("validation_loss")
    trained_at   = data.get("trained_at", "N/A")

    def fmt_pct(v):
        if v is None:
            return "N/A"
        # If already a percentage (> 1) keep as-is, else multiply
        val = float(v)
        return f"{val * 100:.2f}%" if val <= 1.0 else f"{val:.2f}%"

    def fmt_loss(v):
        return f"{float(v):.4f}" if v is not None else "N/A"

    print(f"  Model Name          : {model_name}")
    print(f"  Training Accuracy   : {fmt_pct(train_acc)}")
    print(f"  Validation Accuracy : {fmt_pct(val_acc)}")
    print(f"  Training Loss       : {fmt_loss(train_loss)}")
    print(f"  Validation Loss     : {fmt_loss(val_loss)}")
    print(f"  Trained At          : {trained_at}")
    print(SEP2)
    print(f"  Source              : {source}")
    print(SEP)
    print()


if __name__ == "__main__":
    main()
