"""
train_and_predict.py  —  Train ONCE, Predict EVERY TIME
=========================================================
USAGE
-----
  Train (if needed) + Predict on a specific image:
      python train_and_predict.py --image path/to/image.jpg

  Force retrain + Predict:
      python train_and_predict.py --image path/to/image.jpg --force

  Predict only (no training, model must exist):
      python train_and_predict.py --image path/to/image.jpg --predict-only

  Test model on ALL dataset classes (one sample each):
      python train_and_predict.py --test-all

HOW IT WORKS
------------
  1. Training   : Runs ONCE. Skips if millet_disease_model.h5 already exists
                  (unless --force is passed).
  2. Prediction : Loads the saved model and predicts disease for any image
                  you pass. Works every time without retraining.
"""

import os
import sys
import json
import argparse
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODEL_DIR   = os.path.join(BASE_DIR, "model")
MODEL_PATH  = os.path.join(MODEL_DIR, "millet_disease_model.h5")
LABELS_PATH = os.path.join(MODEL_DIR, "class_names.json")
ACC_PLOT    = os.path.join(MODEL_DIR, "accuracy_plot.png")
LOSS_PLOT   = os.path.join(MODEL_DIR, "loss_plot.png")

# ── Hyper-parameters ─────────────────────────────────────────────────────────
IMG_HEIGHT = 224
IMG_WIDTH  = 224
BATCH_SIZE = 32
MAX_EPOCHS = 20   # EarlyStopping will cut this short when validation plateaus
LR         = 1e-4

# ── Disease info (treatment tips shown after prediction) ─────────────────────
DISEASE_INFO = {
    "Aphid":          "Treatment: Use neem oil spray or insecticidal soap. Remove heavily infested leaves.",
    "Bacterialblight":"Treatment: Use copper-based bactericides. Remove and destroy infected plant material.",
    "Black Rust":     "Treatment: Apply fungicides (mancozeb, propiconazole). Grow resistant varieties.",
    "Blast":          "Treatment: Use tricyclazole fungicide. Avoid excess nitrogen fertilizer.",
    "Brown Rust":     "Treatment: Apply propiconazole or tebuconazole fungicide at early infection.",
    "Healthy":        "No disease detected. Continue regular monitoring and care.",
    "Leaf Blight":    "Treatment: Apply mancozeb fungicide. Ensure proper drainage and crop rotation.",
    "Septoria":       "Treatment: Apply fungicides (azoxystrobin). Maintain good field hygiene.",
    "Smut":           "Treatment: Treat seeds with thiram/carboxin. Remove and burn infected heads.",
    "Stem fly":       "Treatment: Use seed treatment with imidacloprid. Apply carbofuran at sowing.",
    "Tan spot":       "Treatment: Apply propiconazole fungicide. Practice crop rotation.",
    "downy_mildew":   "Treatment: Apply metalaxyl-based fungicides. Use resistant varieties.",
    "rust":           "Treatment: Apply mancozeb or propiconazole. Use resistant varieties.",
}

SEVERITY_COLORS = {
    "Healthy":        "✅",
    "Aphid":          "⚠️",
    "Stem fly":       "⚠️",
    "Bacterialblight":"🔴",
    "Black Rust":     "🔴",
    "Blast":          "🔴",
    "Brown Rust":     "⚠️",
    "Leaf Blight":    "⚠️",
    "Septoria":       "⚠️",
    "Smut":           "🔴",
    "Tan spot":       "⚠️",
    "downy_mildew":   "🔴",
    "rust":           "⚠️",
}


# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 — TRAIN (runs only once unless --force)
# ═════════════════════════════════════════════════════════════════════════════

def train(force: bool = False):
    """Train the MobileNetV2 model. Skips if model already exists."""

    os.makedirs(MODEL_DIR, exist_ok=True)

    # ── Skip if already trained ───────────────────────────────────────────────
    if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH) and not force:
        print("=" * 60)
        print("[INFO] ✅ Trained model already exists — skipping training.")
        print(f"       Model  : {MODEL_PATH}")
        print(f"       Labels : {LABELS_PATH}")
        print("  Tip: Use --force to retrain from scratch.")
        print("=" * 60)
        return

    print("=" * 60)
    print("[START] 🌾 Millet Disease Model Training")
    print(f"  Dataset   : {DATASET_DIR}")
    print(f"  Model out : {MODEL_PATH}")
    print(f"  Force     : {force}")
    print("=" * 60)

    # ── Heavy imports (only when actually training) ───────────────────────────
    import tensorflow as tf
    import matplotlib
    matplotlib.use('Agg')
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

    # Save class names immediately
    with open(LABELS_PATH, 'w') as f:
        json.dump(class_names, f, indent=2)
    print(f"[INFO] Class names saved → {LABELS_PATH}")

    # ── Build MobileNetV2 Transfer Learning model ─────────────────────────────
    base = MobileNetV2(
        input_shape=(IMG_HEIGHT, IMG_WIDTH, 3),
        include_top=False,
        weights='imagenet'
    )
    base.trainable = False  # Freeze base initially

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
    print(f"[INFO] Model built. Total params: {model.count_params():,}")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    callbacks = [
        EarlyStopping(monitor='val_accuracy', patience=5, restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=3, verbose=1, min_lr=1e-7),
        ModelCheckpoint(MODEL_PATH, monitor='val_accuracy', save_best_only=True, verbose=1),
    ]

    # ── Phase 1: Train only the classification head ───────────────────────────
    print("\n[PHASE 1] Training head layers (base frozen) ...")
    history1 = model.fit(
        train_gen,
        epochs=MAX_EPOCHS,
        validation_data=val_gen,
        callbacks=callbacks,
        verbose=1
    )

    # ── Phase 2: Fine-tune the full MobileNetV2 base ──────────────────────────
    print("\n[PHASE 2] Fine-tuning the FULL MobileNetV2 base ...")
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

    # ── Combine histories ─────────────────────────────────────────────────────
    acc      = history1.history['accuracy']     + history2.history['accuracy']
    val_acc  = history1.history['val_accuracy'] + history2.history['val_accuracy']
    loss     = history1.history['loss']         + history2.history['loss']
    val_loss = history1.history['val_loss']     + history2.history['val_loss']

    final_train_acc  = float(acc[-1])
    final_val_acc    = float(val_acc[-1])
    final_train_loss = float(loss[-1])
    final_val_loss   = float(val_loss[-1])

    # Ensure model is saved (ModelCheckpoint saves the best; this is a fallback)
    if not os.path.exists(MODEL_PATH):
        model.save(MODEL_PATH)

    # ── Print results ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  🏆 TRAINING RESULTS")
    print(f"  Training Accuracy   : {final_train_acc * 100:.2f}%")
    print(f"  Validation Accuracy : {final_val_acc * 100:.2f}%")
    print(f"  Training Loss       : {final_train_loss:.4f}")
    print(f"  Validation Loss     : {final_val_loss:.4f}")
    print(f"  Phases: Phase1={len(history1.history['accuracy'])} epochs, "
          f"Phase2={len(history2.history['accuracy'])} epochs")
    print("=" * 60)

    # ── Save accuracy plot ────────────────────────────────────────────────────
    plt.figure(figsize=(10, 5))
    plt.plot(acc,     label='Training Accuracy',   color='#22c55e', linewidth=2)
    plt.plot(val_acc, label='Validation Accuracy', color='#3b82f6', linewidth=2)
    plt.axvline(x=len(history1.history['accuracy']) - 1,
                color='#f59e0b', linestyle='--', alpha=0.7, label='Fine-tune start')
    plt.xlabel("Epoch"); plt.ylabel("Accuracy")
    plt.title("Training vs Validation Accuracy", fontsize=14, fontweight='bold')
    plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(ACC_PLOT, dpi=120, bbox_inches='tight'); plt.close()
    print(f"[SAVED] Accuracy plot → {ACC_PLOT}")

    # ── Save loss plot ────────────────────────────────────────────────────────
    plt.figure(figsize=(10, 5))
    plt.plot(loss,     label='Training Loss',   color='#ef4444', linewidth=2)
    plt.plot(val_loss, label='Validation Loss', color='#f59e0b', linewidth=2)
    plt.axvline(x=len(history1.history['loss']) - 1,
                color='#8b5cf6', linestyle='--', alpha=0.7, label='Fine-tune start')
    plt.xlabel("Epoch"); plt.ylabel("Loss")
    plt.title("Training vs Validation Loss", fontsize=14, fontweight='bold')
    plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
    plt.savefig(LOSS_PLOT, dpi=120, bbox_inches='tight'); plt.close()
    print(f"[SAVED] Loss plot → {LOSS_PLOT}")

    # ── Save metrics to DB ────────────────────────────────────────────────────
    try:
        import sqlite3
        from datetime import datetime
        db_path = os.path.join(BASE_DIR, "instance", "millet.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT,
                    accuracy REAL,
                    loss REAL,
                    training_accuracy REAL,
                    validation_accuracy REAL,
                    validation_loss REAL,
                    trained_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for col, ctype in [("training_accuracy","REAL"),("validation_accuracy","REAL"),("validation_loss","REAL")]:
                try:
                    cursor.execute(f"ALTER TABLE model_metrics ADD COLUMN {col} {ctype}")
                except sqlite3.OperationalError:
                    pass
            cursor.execute("""
                INSERT INTO model_metrics
                    (model_name, accuracy, loss, training_accuracy, validation_accuracy, validation_loss, trained_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("Millet Disease Detection CNN (MobileNetV2)", final_train_acc, final_train_loss,
                  final_train_acc, final_val_acc, final_val_loss,
                  datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); conn.close()
            print("[SAVED] Training metrics → database")
        else:
            print(f"[WARN] DB not found at {db_path} — metrics not saved to DB.")
    except Exception as e:
        print(f"[WARN] Could not save metrics to DB: {e}")

    # ── Save training_results.json ────────────────────────────────────────────
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
            "epochs_phase1":       len(history1.history['accuracy']),
            "epochs_phase2":       len(history2.history['accuracy']),
            "num_classes":         num_classes,
            "class_names":         class_names,
        }
        with open(results_path, "w") as jf:
            json.dump(results, jf, indent=2)
        print(f"[SAVED] Training results → {results_path}")
    except Exception as e:
        print(f"[WARN] Could not save training_results.json: {e}")

    print("\n[DONE] ✅ Training complete! Model ready for predictions.")


# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 — PREDICT (loads saved model, runs every time)
# ═════════════════════════════════════════════════════════════════════════════

def predict(image_path: str):
    """Load the trained model and predict disease for the given image."""

    # ── Validate files ────────────────────────────────────────────────────────
    if not os.path.exists(MODEL_PATH):
        print("[ERROR] Model not found. Run training first (without --predict-only).")
        sys.exit(1)
    if not os.path.exists(LABELS_PATH):
        print("[ERROR] class_names.json not found. Run training first.")
        sys.exit(1)
    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        sys.exit(1)

    import tensorflow as tf
    from PIL import Image

    print("\n" + "=" * 60)
    print("  🔍 MILLET DISEASE PREDICTION")
    print(f"  Image : {image_path}")
    print("=" * 60)

    # ── Load model and class names ────────────────────────────────────────────
    print("[INFO] Loading model ...")
    model = tf.keras.models.load_model(MODEL_PATH)

    with open(LABELS_PATH, 'r') as f:
        class_names = json.load(f)

    # ── Preprocess image ──────────────────────────────────────────────────────
    img = Image.open(image_path).convert('RGB')
    img = img.resize((IMG_HEIGHT, IMG_WIDTH))
    img_array = np.array(img, dtype=np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    # ── Run prediction ────────────────────────────────────────────────────────
    predictions = model.predict(img_array, verbose=0)
    pred_idx    = int(np.argmax(predictions[0]))
    confidence  = float(predictions[0][pred_idx]) * 100
    pred_class  = class_names[pred_idx]

    # ── Top-3 predictions ─────────────────────────────────────────────────────
    top3_idx = np.argsort(predictions[0])[::-1][:3]

    # ── Display results ───────────────────────────────────────────────────────
    icon = SEVERITY_COLORS.get(pred_class, "⚠️")
    info = DISEASE_INFO.get(pred_class, "Consult an agricultural expert.")

    print(f"\n  {icon}  Predicted Disease : {pred_class}")
    print(f"      Confidence      : {confidence:.2f}%")
    print(f"\n  💊 {info}")

    print("\n  📊 Top-3 Predictions:")
    print(f"  {'Rank':<6} {'Disease':<22} {'Confidence':>12}")
    print("  " + "-" * 44)
    for rank, idx in enumerate(top3_idx, 1):
        name = class_names[idx]
        conf = predictions[0][idx] * 100
        bar  = "█" * int(conf / 5)
        print(f"  #{rank:<5} {name:<22} {conf:>8.2f}%  {bar}")

    print("\n" + "=" * 60)
    print("  ✅ Prediction complete!")
    print("     Run again anytime with a new image — model stays loaded.")
    print("=" * 60 + "\n")

    return pred_class, confidence


# ═════════════════════════════════════════════════════════════════════════════
# TEST ALL — predict one sample from each dataset class
# ═════════════════════════════════════════════════════════════════════════════

def test_all_classes():
    """Run prediction on one sample image from each dataset class."""

    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        print("[ERROR] Model not found. Run training first.")
        sys.exit(1)

    import tensorflow as tf
    from PIL import Image

    print("\n" + "=" * 60)
    print("  🧪 TESTING MODEL ON ALL DATASET CLASSES")
    print("=" * 60)

    model = tf.keras.models.load_model(MODEL_PATH)
    with open(LABELS_PATH, 'r') as f:
        class_names = json.load(f)

    correct = 0
    total   = 0

    print(f"\n  {'True Label':<22} {'Predicted':<22} {'Conf':>8}  {'Status'}")
    print("  " + "-" * 65)

    for class_name in class_names:
        class_dir = os.path.join(DATASET_DIR, class_name)
        if not os.path.exists(class_dir):
            print(f"  {'[NOT FOUND]':<22} {class_name}")
            continue

        images = [f for f in os.listdir(class_dir)
                  if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not images:
            print(f"  {class_name:<22} {'[NO IMAGES]':<22}")
            continue

        img_path = os.path.join(class_dir, images[0])
        img      = Image.open(img_path).convert('RGB').resize((IMG_HEIGHT, IMG_WIDTH))
        arr      = np.expand_dims(np.array(img, dtype=np.float32) / 255.0, axis=0)

        preds    = model.predict(arr, verbose=0)
        pred_idx = int(np.argmax(preds[0]))
        pred_cls = class_names[pred_idx]
        conf     = preds[0][pred_idx] * 100
        status   = "✅ CORRECT" if pred_cls == class_name else "❌ WRONG"

        if pred_cls == class_name:
            correct += 1
        total += 1

        print(f"  {class_name:<22} {pred_cls:<22} {conf:>6.1f}%  {status}")

    accuracy = (correct / total * 100) if total > 0 else 0
    print("\n" + "=" * 60)
    print(f"  📊 Overall Accuracy: {correct}/{total} ({accuracy:.1f}%) on sample images")
    print("=" * 60 + "\n")


# ═════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="🌾 Millet Disease Detection — Train once, Predict every time"
    )
    parser.add_argument(
        '--image', type=str, default=None,
        help='Path to the image file to predict disease on.'
    )
    parser.add_argument(
        '--force', action='store_true',
        help='Force retrain the model even if it already exists.'
    )
    parser.add_argument(
        '--predict-only', action='store_true',
        help='Skip training entirely. Only run prediction (model must exist).'
    )
    parser.add_argument(
        '--test-all', action='store_true',
        help='Test model accuracy on one sample from each dataset class.'
    )
    args = parser.parse_args()

    # ── Step 1: Train (once) ──────────────────────────────────────────────────
    if not args.predict_only and not args.test_all:
        train(force=args.force)

    # ── Step 2: Predict ───────────────────────────────────────────────────────
    if args.test_all:
        test_all_classes()
    elif args.image:
        predict(args.image)
    else:
        # No image passed — run test-all as default demo
        print("\n[INFO] No --image specified. Running demo on all dataset classes ...\n")
        test_all_classes()
