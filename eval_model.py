import os
import json
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "millet_disease_model.h5")
LABELS_PATH = os.path.join(BASE_DIR, "model", "class_names.json")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

def evaluate_model():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        print("Model or labels not found.")
        return

    with open(LABELS_PATH, 'r') as f:
        class_names = json.load(f)

    print(f"Loading model for evaluation...")
    import tensorflow as tf
    model = tf.keras.models.load_model(MODEL_PATH)
    
    print(f"Evaluating on classes: {class_names}")

    datagen = ImageDataGenerator(rescale=1.0 / 255)
    
    # CRITICAL: Must use the same class order as training
    eval_generator = datagen.flow_from_directory(
        DATASET_DIR,
        target_size=(224, 224),
        batch_size=32,
        class_mode="categorical",
        classes=class_names,  # Force consistent indexing
        shuffle=False         # Better for evaluation
    )

    if eval_generator.samples == 0:
        print(f"[ERROR] No images found in {DATASET_DIR}")
        return

    print(f"Running evaluation on {eval_generator.samples} images...")
    results = model.evaluate(eval_generator, verbose=1)
    
    print("\n" + "="*40)
    print(f"  Model accuracy on dataset: {results[1]*100:.2f}%")
    print(f"  Model loss:               {results[0]:.4f}")
    print("="*40)

if __name__ == '__main__':
    evaluate_model()
