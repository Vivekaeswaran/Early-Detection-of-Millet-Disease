import os
import json
import numpy as np
import tensorflow as tf
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "millet_disease_model.h5")
LABELS_PATH = os.path.join(BASE_DIR, "model", "class_names.json")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

def test_manual():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(LABELS_PATH):
        print("Model or labels not found.")
        return

    model = tf.keras.models.load_model(MODEL_PATH)
    with open(LABELS_PATH, 'r') as f:
        class_names = json.load(f)

    for class_name in class_names:
        class_dir = os.path.join(DATASET_DIR, class_name)
        if not os.path.exists(class_dir):
            print(f"Directory not found: {class_dir}")
            continue
        
        images = [f for f in os.listdir(class_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not images:
            continue
            
        img_path = os.path.join(class_dir, images[0])
        img_pil = Image.open(img_path).convert('RGB')
        img_resized = img_pil.resize((224, 224))
        img_array = np.array(img_resized, dtype=np.float32) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        predictions = model.predict(img_array, verbose=0)
        pred_idx = np.argmax(predictions[0])
        pred_label = class_names[pred_idx]
        confidence = predictions[0][pred_idx]

        print(f"True: {class_name:20} | Pred: {pred_label:20} | Conf: {confidence:.4f}")

if __name__ == '__main__':
    test_manual()
