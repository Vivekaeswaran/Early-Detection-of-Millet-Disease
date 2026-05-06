"""
train_model.py  —  Manual-only training script
===============================================
USAGE
-----
  Train only if model doesn't exist:
      python train_model.py

  Force retraining even if model already exists:
      python train_model.py --force

IMPORTANT
---------
This script does NOT run automatically on app startup.
It must be executed explicitly from the command line OR
triggered via the Admin Panel → "Retrain Model" button.
"""

import os
import sys
import json
import argparse
import numpy as np

# ── Paths (always relative to THIS file, not CWD) ────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODEL_DIR   = os.path.join(BASE_DIR, "model")
MODEL_PATH  = os.path.join(MODEL_DIR, "millet_disease_model.h5")
LABELS_PATH = os.path.join(MODEL_DIR, "class_names.json")
ACC_PLOT    = os.path.join(MODEL_DIR, "accuracy_plot.png")
LOSS_PLOT   = os.path.join(MODEL_DIR, "loss_plot.png")

# ── Hyper-parameters ─────────────────────────────────────────────────────────
IMG_HEIGHT  = 224
IMG_WIDTH   = 224
BATCH_SIZE  = 32
MAX_EPOCHS  = 20   # EarlyStopping will stop sooner if needed
LR          = 1e-4


def train(force: bool = False):
    """Full training pipeline. Skips if model exists and force=False."""

    os.makedirs(MODEL_DIR, exist_ok=True)

    # ── Skip check ───────────────────────────────────────────────────────────
    if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH) and not force:
        print("="*60)
        print("[INFO] Trained model already exists.")
        print(f"       Model  : {MODEL_PATH}")
        print(f"       Labels : {LABELS_PATH}")
        print("  To retrain, run:  python train_model.py --force")
        print("="*60)
        return

    print("="*60)
    print("[START] Millet Disease Model Training")
    print(f"  Dataset  : {DATASET_DIR}")
    print(f"  Model out: {MODEL_PATH}")
    print(f"  Force    : {force}")
    print("="*60)

    # ── Imports (heavy; only loaded when actually training) ───────────────────
    import tensorflow as tf
    import matplotlib
    matplotlib.use('Agg')   # Non-interactive backend (safe for servers)
    import matplotlib.pyplot as plt
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout, BatchNormalization
    from tensorflow.keras.models import Model
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

    print(f"[INFO] TensorFlow version: {tf.__version__}")

    # ── Data generators ───────────────────────────────────────────────────────
    datagen = ImageDataGenerator(
        rescale=1.0 / 255,
        validation_split=0.2,
        rotation_range=20,
        zoom_range=0.2,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        fill_mode='nearest'
    )

    train_gen = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        subset="training",
        shuffle=True
    )

    val_gen = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        subset="validation",
        shuffle=False
    )

    class_names = list(train_gen.class_indices.keys())
    num_classes = len(class_names)
    print(f"[INFO] Classes ({num_classes}): {class_names}")

    # Save class names immediately so they're available even if training fails
    with open(LABELS_PATH, 'w') as f:
        json.dump(class_names, f, indent=2)
    print(f"[INFO] Class names saved → {LABELS_PATH}")

    # ── Build model (MobileNetV2 Transfer Learning) ───────────────────────────
    base = MobileNetV2(
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        include_top=False,
        weights='imagenet'
    )
    # Freeze base initially
    base.trainable = False

    x = base.output
    x = GlobalAveragePooling2D()(x)
    x = BatchNormalization()(x)
    x = Dense(256, activation='relu')(x)
    x = Dropout(0.4)(x)
    x = Dense(128, activation='relu')(x)
    x = Dropout(0.3)(x)
    outputs = Dense(num_classes, activation='softmax')(x)

    model = Model(inputs=base.input, outputs=outputs)

    model.compile(
        optimizer=Adam(learning_rate=LR),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    print(f"[INFO] Model built. Trainable params: {model.count_params():,}")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    callbacks = [
        EarlyStopping(monitor='val_accuracy', patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=3, verbose=1, min_lr=1e-7),
        ModelCheckpoint(MODEL_PATH, monitor='val_accuracy', save_best_only=True, verbose=1),
    ]

    # ── Phase 1: Train only the head ──────────────────────────────────────────
    print("\n[PHASE 1] Training head layers (base frozen) ...")
    history = model.fit(
        train_gen,
        epochs=MAX_EPOCHS,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )

    # ── Phase 2: Fine-tune ALL layers of base ─────────────────────────────────
    print("\n[PHASE 2] Fine-tuning the FULL MobileNetV2 base model ...")
    base.trainable = True

    model.compile(
        optimizer=Adam(learning_rate=LR / 10),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )

    history2 = model.fit(
        train_gen,
        epochs=MAX_EPOCHS,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )

    # ── Combine history from both phases ─────────────────────────────────────
    combined_acc     = history.history['accuracy']     + history2.history['accuracy']
    combined_val_acc = history.history['val_accuracy'] + history2.history['val_accuracy']
    combined_loss    = history.history['loss']         + history2.history['loss']
    combined_val_loss= history.history['val_loss']     + history2.history['val_loss']

    final_train_acc = float(combined_acc[-1])
    final_val_acc   = float(combined_val_acc[-1])
    final_train_loss= float(combined_loss[-1])
    final_val_loss  = float(combined_val_loss[-1])

    # ── Save model explicitly (best already saved by checkpoint) ─────────────
    if not os.path.exists(MODEL_PATH):
        model.save(MODEL_PATH)
    print(f"\n[SAVED] Model → {MODEL_PATH}")

    # ── Print final metrics ───────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  TRAINING RESULTS")
    print(f"  Training Accuracy   : {final_train_acc*100:.2f}%")
    print(f"  Validation Accuracy : {final_val_acc*100:.2f}%")
    print(f"  Training Loss       : {final_train_loss:.4f}")
    print(f"  Validation Loss     : {final_val_loss:.4f}")
    print("="*60)

    # ── Save accuracy plot ────────────────────────────────────────────────────
    plt.figure(figsize=(10, 5))
    plt.plot(combined_acc,     label='Training Accuracy',   color='#22c55e', linewidth=2)
    plt.plot(combined_val_acc, label='Validation Accuracy', color='#3b82f6', linewidth=2)
    plt.axvline(x=len(history.history['accuracy'])-1, color='#f59e0b',
                linestyle='--', alpha=0.7, label='Fine-tune start')
    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("Accuracy", fontsize=12)
    plt.title("Training vs Validation Accuracy", fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(ACC_PLOT, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] Accuracy plot → {ACC_PLOT}")

    # ── Save loss plot ────────────────────────────────────────────────────────
    plt.figure(figsize=(10, 5))
    plt.plot(combined_loss,     label='Training Loss',   color='#ef4444', linewidth=2)
    plt.plot(combined_val_loss, label='Validation Loss', color='#f59e0b', linewidth=2)
    plt.axvline(x=len(history.history['loss'])-1, color='#8b5cf6',
                linestyle='--', alpha=0.7, label='Fine-tune start')
    plt.xlabel("Epoch", fontsize=12)
    plt.ylabel("Loss", fontsize=12)
    plt.title("Training vs Validation Loss", fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(LOSS_PLOT, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"[SAVED] Loss plot → {LOSS_PLOT}")

    # ── Save metrics to DB ────────────────────────────────────────────────────
    try:
        # Use raw SQLite so this script stays independent of Flask app context
        import sqlite3
        from datetime import datetime

        db_path = os.path.join(BASE_DIR, "instance", "millet.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Ensure table + columns exist (safe if already there)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name          TEXT,
                    accuracy            REAL,
                    loss                REAL,
                    training_accuracy   REAL,
                    validation_accuracy REAL,
                    validation_loss     REAL,
                    trained_at          DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for col, ctype in [
                ("training_accuracy",   "REAL"),
                ("validation_accuracy", "REAL"),
                ("validation_loss",     "REAL"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE model_metrics ADD COLUMN {col} {ctype}")
                except sqlite3.OperationalError:
                    pass  # Column already exists

            cursor.execute("""
                INSERT INTO model_metrics
                    (model_name, accuracy, loss, training_accuracy, validation_accuracy, validation_loss, trained_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "Millet Disease Detection CNN (MobileNetV2)",
                final_train_acc,
                final_train_loss,
                final_train_acc,
                final_val_acc,
                final_val_loss,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ))
            conn.commit()
            conn.close()
            print("[SAVED] Training metrics → database (model_metrics table)")
        else:
            print(f"[WARN] DB not found at {db_path} — metrics NOT saved to DB.")
            print("  Start the Flask app first, then re-run training if needed.")
    except Exception as e:
        print(f"[WARN] Could not save metrics to DB: {e}")
        print("  Training itself succeeded. Metrics are printed above.")

    # ── Save metrics to training_results.json (check_accuracy.py reads this) ──
    try:
        from datetime import datetime
        results_path = os.path.join(MODEL_DIR, "training_results.json")
        results = {
            "model_name":          "millet_disease_model.h5",
            "training_accuracy":   round(final_train_acc * 100, 4),
            "validation_accuracy": round(final_val_acc  * 100, 4),
            "loss":                round(final_train_loss, 6),
            "validation_loss":     round(final_val_loss,  6),
            "trained_at":          datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "epochs_phase1":       len(history.history['accuracy']),
            "epochs_phase2":       len(history2.history['accuracy']),
            "num_classes":         num_classes,
            "class_names":         class_names,
        }
        with open(results_path, "w") as jf:
            json.dump(results, jf, indent=2)
        print(f"[SAVED] Training results JSON → {results_path}")
    except Exception as e:
        print(f"[WARN] Could not save training_results.json: {e}")

    print("\n[DONE] Training complete!")
    print("       The app will automatically use the new model on next prediction.")
    print("       Run: python check_accuracy.py   to view training metrics anytime.")


def resume_phase2():
    """
    Resume training from Phase 2 only.
    Loads the existing saved model (from Phase 1) and runs Phase 2 fine-tuning.
    Use this when training was interrupted during Phase 2.
    """
    os.makedirs(MODEL_DIR, exist_ok=True)

    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        print("[ERROR] No saved model found. Run full training first:")
        print("        python train_model.py --force")
        return

    print("=" * 60)
    print("[RESUME] Resuming from Phase 2 Fine-Tuning")
    print(f"  Loading model : {MODEL_PATH}")
    print("=" * 60)

    import tensorflow as tf
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from tensorflow.keras.preprocessing.image import ImageDataGenerator
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint

    print(f"[INFO] TensorFlow version: {tf.__version__}")

    # Load existing model
    model = tf.keras.models.load_model(MODEL_PATH)
    print(f"[INFO] Model loaded successfully.")

    # Load class names
    with open(LABELS_PATH, 'r') as f:
        import json
        class_names = json.load(f)
    num_classes = len(class_names)
    print(f"[INFO] Classes ({num_classes}): {class_names}")

    # Data generators
    datagen = ImageDataGenerator(
        rescale=1.0 / 255,
        validation_split=0.2,
        rotation_range=20,
        zoom_range=0.2,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        fill_mode='nearest'
    )
    train_gen = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        subset="training",
        shuffle=True
    )
    val_gen = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=(IMG_HEIGHT, IMG_WIDTH),
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        subset="validation",
        shuffle=False
    )

    # Unfreeze ALL layers for fine-tuning
    for layer in model.layers:
        layer.trainable = True

    model.compile(
        optimizer=Adam(learning_rate=LR / 10),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    print(f"[INFO] All layers unfrozen. Starting Phase 2 fine-tuning ...")

    callbacks = [
        EarlyStopping(monitor='val_accuracy', patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=3, verbose=1, min_lr=1e-7),
        ModelCheckpoint(MODEL_PATH, monitor='val_accuracy', save_best_only=True, verbose=1),
    ]

    print("\n[PHASE 2] Fine-tuning the FULL MobileNetV2 base model ...")
    history2 = model.fit(
        train_gen,
        epochs=MAX_EPOCHS,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )

    final_train_acc  = float(history2.history['accuracy'][-1])
    final_val_acc    = float(history2.history['val_accuracy'][-1])
    final_train_loss = float(history2.history['loss'][-1])
    final_val_loss   = float(history2.history['val_loss'][-1])

    print("\n" + "=" * 60)
    print("  PHASE 2 RESULTS (Resumed)")
    print(f"  Training Accuracy   : {final_train_acc * 100:.2f}%")
    print(f"  Validation Accuracy : {final_val_acc * 100:.2f}%")
    print(f"  Training Loss       : {final_train_loss:.4f}")
    print(f"  Validation Loss     : {final_val_loss:.4f}")
    print("=" * 60)

    # Save training_results.json
    try:
        from datetime import datetime
        results_path = os.path.join(MODEL_DIR, "training_results.json")
        results = {
            "model_name":          "millet_disease_model.h5",
            "training_accuracy":   round(final_train_acc * 100, 4),
            "validation_accuracy": round(final_val_acc  * 100, 4),
            "loss":                round(final_train_loss, 6),
            "validation_loss":     round(final_val_loss,  6),
            "trained_at":          datetime.now().strftime("%Y-%m-%d %I:%M %p"),
            "epochs_phase2":       len(history2.history['accuracy']),
            "num_classes":         num_classes,
            "class_names":         class_names,
            "resumed":             True
        }
        with open(results_path, "w") as jf:
            json.dump(results, jf, indent=2)
        print(f"[SAVED] Training results → {results_path}")
    except Exception as e:
        print(f"[WARN] Could not save training_results.json: {e}")

    print("\n[DONE] Phase 2 Resume complete! ✅")
    print("       Run: python app.py   to start the app with the new model.")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Train the Millet Disease Detection CNN model."
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Force retraining even if millet_disease_model.h5 already exists.'
    )
    parser.add_argument(
        '--resume', action='store_true',
        help='Resume Phase 2 fine-tuning from the existing saved model (use after Ctrl+C during Phase 2).'
    )
    args = parser.parse_args()

    if args.resume:
        resume_phase2()
    else:
        train(force=args.force)