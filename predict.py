import os
import json
import numpy as np
import tensorflow as tf
import cv2

model_path = os.path.join("model", "millet_disease_model.h5")
labels_path = os.path.join("model", "class_names.json")

# Load trained model
model = tf.keras.models.load_model(model_path)

# Load class names dynamically
with open(labels_path, 'r') as f:
    classes = json.load(f)

# Test image path
image_path = "images/test2.jpeg"
img = cv2.imread(image_path)

if img is None:
    print("Error: Image not found. Check the file path.")
    exit()

img = cv2.resize(img, (224, 224))
img = img / 255.0
img = np.expand_dims(img, axis=0)

prediction = model.predict(img)
predicted_index = np.argmax(prediction)
predicted_class = classes[predicted_index]
confidence = np.max(prediction) * 100

print("Predicted Disease:", predicted_class)
print("Confidence: {:.2f}%".format(confidence))
print("Prediction Values:", prediction)