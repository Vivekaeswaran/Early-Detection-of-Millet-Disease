import os
from tensorflow.keras.preprocessing.image import ImageDataGenerator, load_img, img_to_array

# Class folders
folders = [
    "dataset/blast",
    "dataset/rust",
    "dataset/healthy",
    "dataset/downy_mildew"
]

# Augmentation settings
datagen = ImageDataGenerator(
    rotation_range=25,
    width_shift_range=0.1,
    height_shift_range=0.1,
    shear_range=0.1,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode="nearest"
)

target_count = 40  # total images needed per class

for folder in folders:
    images = [f for f in os.listdir(folder) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    current_count = len(images)

    print(f"\nFolder: {folder}")
    print(f"Current images: {current_count}")

    if current_count == 0:
        print("No images found in this folder.")
        continue

    if current_count >= target_count:
        print("Already enough images.")
        continue

    needed = target_count - current_count
    print(f"Creating {needed} augmented images...")

    generated = 0

    for img_name in images:
        if generated >= needed:
            break

        img_path = os.path.join(folder, img_name)
        img = load_img(img_path, target_size=(224, 224))
        x = img_to_array(img)
        x = x.reshape((1,) + x.shape)

        prefix_name = os.path.splitext(img_name)[0]

        for batch in datagen.flow(
            x,
            batch_size=1,
            save_to_dir=folder,
            save_prefix=f"aug_{prefix_name}",
            save_format="jpg"
        ):
            generated += 1
            if generated >= needed:
                break

    print(f"Done. Total images should now be around {target_count}.")

print("\nImage augmentation completed successfully.")