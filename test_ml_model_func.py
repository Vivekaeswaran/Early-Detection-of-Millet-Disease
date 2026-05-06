import os
import time
from ml_model import predict_disease

# Use the test image that's in the directory
img_path = 'test_img.jpg'
if not os.path.exists(img_path):
    # Try to find one in dataset
    for root, dirs, files in os.walk('dataset'):
        for f in files:
            if f.lower().endswith(('.jpg', '.png')):
                img_path = os.path.join(root, f)
                break
        if img_path != 'test_img.jpg': break

print(f"Testing prediction on: {img_path}\n")

print("--- CALL 1 ---")
start = time.time()
res1 = predict_disease(img_path)
end = time.time()
print(f"Call 1 took: {end-start:.2f}s")

print("\n--- CALL 2 ---")
start = time.time()
res2 = predict_disease(img_path)
end = time.time()
print(f"Call 2 took: {end-start:.2f}s")

print(f"\nResult success: {res1['success']} (1), {res2['success']} (2)")
