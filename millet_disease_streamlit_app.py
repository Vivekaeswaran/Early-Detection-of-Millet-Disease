import os

import cv2
import numpy as np
import streamlit as st
import tensorflow as tf
from PIL import Image

st.set_page_config(
    page_title="Millet Disease Detection App",
    page_icon="🌾",
    layout="wide",
)

# -------------------------------------------------
# Disease knowledge base
# -------------------------------------------------
DISEASE_INFO = {
    "blast": {
        "title": "Blast Disease",
        "about": "Blast is a fungal disease that can damage leaves, neck, and ear heads. Early detection helps reduce spread and crop loss.",
        "dos": [
            "Remove severely infected leaves or plants if infection is localized.",
            "Use resistant or tolerant varieties in the next season.",
            "Maintain proper spacing for better air circulation.",
            "Keep the field clean and remove infected crop residues.",
            "Use balanced fertilizer and avoid too much nitrogen.",
        ],
        "donts": [
            "Do not overcrowd plants.",
            "Do not leave infected residues in the field.",
            "Do not over-irrigate and keep leaves wet for long periods.",
            "Do not spray chemicals without local expert guidance.",
        ],
        "treatments": [
            "Use fungicide only if recommended by local agriculture experts.",
            "Seed treatment and preventive crop management are useful.",
            "Integrated management gives better results than using only chemicals.",
        ],
        "recovery": [
            "Monitor nearby plants regularly.",
            "Improve sanitation and field management.",
            "Use clean seed and rotate crops in the next season.",
        ],
    },
    "downy_mildew": {
        "title": "Downy Mildew",
        "about": "Downy mildew spreads through infected seed and field-borne spores. It can weaken plants and reduce yield significantly.",
        "dos": [
            "Remove infected plants early if possible.",
            "Use certified disease-free seed.",
            "Practice crop rotation with non-host crops.",
            "Improve drainage and avoid water stagnation.",
            "Use resistant varieties where available.",
        ],
        "donts": [
            "Do not reuse seed from infected plants.",
            "Do not keep infected debris in the field.",
            "Do not allow standing water for long periods.",
            "Do not ignore early yellowing or fungal symptoms.",
        ],
        "treatments": [
            "Seed treatment may help reduce risk in the next crop.",
            "For severe infection, consult local agriculture experts for approved fungicides.",
            "Combine sanitation, resistant seed, and field management for best results.",
        ],
        "recovery": [
            "Remove badly affected plants where practical.",
            "Improve drainage and reduce humidity around the crop.",
            "Use resistant seed in the next season.",
        ],
    },
    "healthy": {
        "title": "Healthy Leaf",
        "about": "The uploaded image is predicted as healthy. Continue good crop management practices.",
        "dos": [
            "Continue routine crop monitoring.",
            "Maintain balanced irrigation and fertilization.",
            "Keep the field clean and control weeds.",
            "Use quality seed and follow good agricultural practices.",
        ],
        "donts": [
            "Do not ignore new spots or yellowing later.",
            "Do not overuse fertilizer or water.",
            "Do not allow water stagnation in the field.",
        ],
        "treatments": [
            "No treatment needed right now.",
            "Only preventive care and monitoring are required.",
        ],
        "recovery": [
            "Keep observing the crop regularly.",
            "Upload a fresh image again if any symptoms appear later.",
        ],
    },
    "rust": {
        "title": "Rust Disease",
        "about": "Rust appears as orange or brown pustules on leaves and can reduce plant vigor if it spreads widely.",
        "dos": [
            "Use resistant varieties when possible.",
            "Scout fields regularly after symptoms start.",
            "Remove volunteer plants and infected residues.",
            "Improve air movement with proper spacing.",
            "Keep the crop healthy with balanced nutrients.",
        ],
        "donts": [
            "Do not ignore orange or brown spots on leaves.",
            "Do not keep infected debris after harvest.",
            "Do not depend only on chemical control.",
        ],
        "treatments": [
            "Integrated management is preferred.",
            "Use fungicides only if recommended locally and economically feasible.",
            "Sanitation and resistant varieties are important long-term solutions.",
        ],
        "recovery": [
            "Track disease spread in nearby plants.",
            "Remove infected residues after harvest.",
            "Choose resistant seed next season if rust was serious.",
        ],
    },
}

CLASS_NAMES = ["blast", "downy_mildew", "healthy", "rust"]
MODEL_PATH = "millet_disease_model.h5"
IMAGE_SIZE = (224, 224)


@st.cache_resource
def load_model(path: str):
    if not os.path.exists(path):
        return None
    return tf.keras.models.load_model(path)


def preprocess_image(uploaded_image: Image.Image):
    image = uploaded_image.convert("RGB")
    img_array = np.array(image)
    img_array = cv2.resize(img_array, IMAGE_SIZE)
    img_array = img_array / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return image, img_array


def predict_disease(model, img_array):
    preds = model.predict(img_array, verbose=0)[0]
    pred_index = int(np.argmax(preds))
    pred_class = CLASS_NAMES[pred_index]
    confidence = float(preds[pred_index]) * 100
    return pred_class, confidence, preds


def styled_box(title: str, items, color: str):
    if isinstance(items, str):
        content = f"<p style='margin:0'>{items}</p>"
    else:
        content = "<ul>" + "".join([f"<li>{item}</li>" for item in items]) + "</ul>"

    st.markdown(
        f"""
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-left:6px solid {color};padding:16px;border-radius:16px;margin-bottom:16px;box-shadow:0 2px 10px rgba(0,0,0,0.05)">
            <h4 style="margin-top:0">{title}</h4>
            {content}
        </div>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------
# App state
# -------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 1

if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

if "pred_class" not in st.session_state:
    st.session_state.pred_class = None

if "confidence" not in st.session_state:
    st.session_state.confidence = None

if "all_scores" not in st.session_state:
    st.session_state.all_scores = None


# -------------------------------------------------
# Header
# -------------------------------------------------
st.markdown(
    """
    <div style="text-align:center;padding:10px 0 6px 0;">
        <h1 style="margin-bottom:6px;">🌾 Millet Disease Detection App</h1>
        <p style="font-size:18px;color:#4b5563;">Step-by-step interface for disease prediction, treatment support, and recovery guidance.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

model = load_model(MODEL_PATH)
if model is None:
    st.error("Model file 'millet_disease_model.h5' not found. Keep it in the same folder as this app.")
    st.stop()

# -------------------------------------------------
# Sidebar progress
# -------------------------------------------------
st.sidebar.title("App Flow")
st.sidebar.markdown(
    f"""
    **Step 1** - Upload Image {'✅' if st.session_state.step > 1 else '⬅️'}

    **Step 2** - Predict Disease {'✅' if st.session_state.step > 2 else '⬅️'}

    **Step 3** - View Result {'✅' if st.session_state.step > 3 else '⬅️'}

    **Step 4** - Read Do's / Don'ts / Treatment / Recovery {'✅' if st.session_state.step > 4 else '⬅️'}
    """
)

if st.sidebar.button("Reset App"):
    st.session_state.step = 1
    st.session_state.uploaded_image = None
    st.session_state.pred_class = None
    st.session_state.confidence = None
    st.session_state.all_scores = None
    st.rerun()

# -------------------------------------------------
# Step 1: Upload
# -------------------------------------------------
st.markdown("## Step 1: Upload Millet Leaf Image")
uploaded_file = st.file_uploader("Choose a leaf image", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    pil_image = Image.open(uploaded_file)
    st.session_state.uploaded_image = pil_image
    st.session_state.step = max(st.session_state.step, 2)
    st.image(pil_image, caption="Uploaded Leaf Image", use_container_width=True)

# -------------------------------------------------
# Step 2: Predict
# -------------------------------------------------
st.markdown("## Step 2: Run Disease Prediction")
if st.session_state.uploaded_image is not None:
    if st.button("Predict Now", use_container_width=True):
        preview_image, processed_array = preprocess_image(st.session_state.uploaded_image)
        pred_class, confidence, all_scores = predict_disease(model, processed_array)

        st.session_state.pred_class = pred_class
        st.session_state.confidence = confidence
        st.session_state.all_scores = all_scores.tolist()
        st.session_state.step = 3
        st.rerun()
else:
    st.info("Please upload an image first.")

# -------------------------------------------------
# Step 3: Result
# -------------------------------------------------
if st.session_state.pred_class is not None:
    st.markdown("## Step 3: Prediction Result")
    disease = DISEASE_INFO[st.session_state.pred_class]

    col1, col2 = st.columns([1, 1])
    with col1:
        st.success(f"Predicted Disease: {disease['title']}")
        st.metric("Confidence", f"{st.session_state.confidence:.2f}%")
        st.info(disease["about"])

    with col2:
        st.markdown("### Class Probabilities")
        for label, score in zip(CLASS_NAMES, st.session_state.all_scores):
            st.write(f"**{label}**")
            st.progress(min(max(float(score), 0.0), 1.0))
            st.caption(f"{float(score) * 100:.2f}%")

    st.session_state.step = max(st.session_state.step, 4)

# -------------------------------------------------
# Step 4: Actions and advice
# -------------------------------------------------
if st.session_state.pred_class is not None:
    st.markdown("## Step 4: Recommended Actions")
    disease = DISEASE_INFO[st.session_state.pred_class]

    a, b = st.columns(2)
    c, d = st.columns(2)

    with a:
        styled_box("✅ Do's", disease["dos"], "#16a34a")
    with b:
        styled_box("❌ Don'ts", disease["donts"], "#dc2626")
    with c:
        styled_box("💊 Treatment", disease["treatments"], "#2563eb")
    with d:
        styled_box("🌱 Recovery / Next Steps", disease["recovery"], "#7c3aed")

    st.session_state.step = 5

st.markdown("---")
st.subheader("Run Command")
st.code(
    "python -m pip install streamlit pillow tensorflow opencv-python numpy\npython -m streamlit run millet_disease_streamlit_app.py",
    language="bash",
)

st.caption(
    "This app provides model-based prediction and general crop-care guidance. Final field treatment decisions should be confirmed with local agriculture experts."
)
