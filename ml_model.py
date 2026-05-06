import os
import random
import hashlib
import threading
from PIL import Image
import numpy as np
import json

# ─────────────────────────────────────────────
# Global Model Cache (Singleton)
# ─────────────────────────────────────────────
_MODEL = None
_CLASS_NAMES = None
_MODEL_LOCK = threading.Lock()
# Disease Knowledge Base
# ─────────────────────────────────────────────
DISEASE_DB = {
    "Healthy": {
        "description": "The millet crop appears healthy with no visible signs of disease. Continue good agricultural practices to maintain crop health throughout the growing season.",
        "symptoms": "No disease symptoms detected. Plant shows normal green coloration, upright growth, and well-formed panicles.",
        "severity_range": (0.0, 0.0),
        "treatment": "No treatment required. Continue regular monitoring and preventive care.",
        "chemicals": "No chemicals needed. Consider preventive spray of Neem-based bioinsecticide (0.3%) as a prophylactic measure.",
        "fertilizers": "Apply recommended NPK (80:40:40 kg/ha) in split doses. Top-dress urea at knee-high stage (20-25 DAS). Micronutrients: ZnSO4 @ 25 kg/ha.",
        "prevention": "Continue crop rotation; regular field monitoring; maintain proper plant population; irrigate at critical stages (boot leaf, flowering, grain filling).",
        "dos": "Monitor weekly; maintain weed-free field; follow proper irrigation schedule; apply balanced fertilizer; practice good field hygiene.",
        "donts": "Do not over-irrigate; do not over-apply nitrogen; do not neglect pest scouting even in healthy crops."
    },
    "Blast": {
        "description": "Millet blast caused by Pyricularia grisea is a serious fungal disease that attacks leaves, nodes, and ear heads during humid weather conditions.",
        "symptoms": "Spindle-shaped lesions with grey center and brown border on leaves; neck rot causing the panicle to turn grey and die; severe lodging; blasting of grains leading to poor grain filling.",
        "severity_range": (0.50, 0.88),
        "treatment": "Spray Tricyclazole 75% WP at 0.6g/L or Carbendazim 50% WP at 1g/L. Apply two sprays at 10-day intervals starting from boot leaf stage.",
        "chemicals": "Tricyclazole 75% WP (0.6g/L), Carbendazim 50% WP (1g/L), Isoprothiolane 40% EC (1.5 ml/L), Propiconazole 25% EC (1ml/L).",
        "fertilizers": "Avoid excessive nitrogen; use split application of N fertilizer; apply silica-rich fertilizers to strengthen cell walls. NPK ratio 80:40:40 kg/ha.",
        "prevention": "Grow blast-resistant varieties; avoid high nitrogen fertilization; ensure good plant spacing for air circulation; avoid late sowing; remove crop debris after harvest.",
        "dos": "Monitor field regularly; apply fungicide at early blast sign; maintain proper plant spacing; spray silicon foliar spray.",
        "donts": "Do not apply excess nitrogen; do not grow susceptible varieties in blast-prone areas; do not irrigate during evening hours."
    },
    "Downy Mildew": {
        "description": "Downy mildew is a fungal-like disease caused by Sclerospora graminicola. It is one of the most destructive diseases of pearl millet, causing significant yield losses worldwide.",
        "symptoms": "Yellow chlorotic streaks or patches on leaves; white powdery fungal growth on underside of leaves; stunted plant growth; partial or complete sterility of the ear head; excessive tillering (witches broom effect).",
        "severity_range": (0.55, 0.92),
        "treatment": "Apply Metalaxyl-based fungicide (Ridomil Gold) at the rate of 2.5g/kg seed. Remove and destroy infected plants immediately. Avoid water stagnation near the field.",
        "chemicals": "Metalaxyl 35% WS (2.5g/kg seed), Mancozeb 75% WP (2.5kg/ha spray), Cymoxanil + Mancozeb (3g/L foliar spray).",
        "fertilizers": "Apply balanced NPK (90:45:45 kg/ha). Increase Potassium to boost plant immunity. Add micronutrient zinc sulphate @ 25kg/ha.",
        "prevention": "Use resistant varieties (HHB 67, HC-20); treat seeds with metalaxyl before sowing; practice crop rotation with non-host crops; avoid overhead irrigation; maintain proper field drainage.",
        "dos": "Use certified disease-free seeds; apply seed treatment before sowing; remove infected plants early; spray fungicide at first sign of disease.",
        "donts": "Do not use infected seeds; do not flood irrigate; do not compost infected plant material; avoid monoculture."
    },
    "Rust": {
        "description": "Millet rust caused by Puccinia substriata var. indica produces reddish-brown pustules on leaves and sheaths. It reduces photosynthesis and grain quality.",
        "symptoms": "Small reddish-brown to orange-yellow pustules on upper and lower leaf surfaces; yellowing and drying of leaves from tips; reduced grain weight; early senescence.",
        "severity_range": (0.45, 0.85),
        "treatment": "Apply Mancozeb 75% WP at 2.5 kg/ha or Propiconazole 25% EC at 1ml/L. First spray at disease appearance; second spray 15 days later.",
        "chemicals": "Mancozeb 75% WP (2.5kg/ha), Propiconazole 25% EC (1ml/L), Tebuconazole 25.9% EC (1ml/L), Hexaconazole 5% SC (2ml/L).",
        "fertilizers": "Balanced potassic fertilization improves rust resistance. Apply MOP @ 60 kg/ha. Reduce excessive nitrogen application.",
        "prevention": "Use rust-tolerant varieties; practice early sowing to avoid peak rust season; remove volunteer crop plants; apply preventive fungicide sprays.",
        "dos": "Spray at early disease stage; use resistant varieties; monitor crops weekly; ensure field sanitation.",
        "donts": "Do not delay spraying; do not use infected plant material as mulch; do not grow millet repeatedly in same field without rotation."
    },
    "Leaf Spot": {
        "description": "Leaf spot diseases are caused by various fungi resulting in localized dead tissue on leaves, reducing photosynthetic area.",
        "symptoms": "Small, scattered brown to dark brown spots on leaves; spots may coalesce causing leaf blight; premature drying of older leaves.",
        "severity_range": (0.35, 0.70),
        "treatment": "Apply broad-spectrum fungicides like Mancozeb or Chlorothalonil early in the disease cycle.",
        "chemicals": "Mancozeb 75% WP (2.5g/L), Chlorothalonil 75% WP (2g/L), Propineb 70% WP (2g/L).",
        "fertilizers": "Maintain balanced NPK. Foliar spray of Potassium Phosphate can help.",
        "prevention": "Remove affected leaves early; maintain good weed control; avoid dense planting.",
        "dos": "Ensure field drainage; practice crop rotation.",
        "donts": "Do not allow water droplets to remain on leaves over night if possible."
    },
    "Smut": {
        "description": "Covered kernel smut caused by Moesziomyces penicillariae replaces grain with masses of black smut spores, rendering the entire ear head useless.",
        "symptoms": "Entire ear head replaced by dark brown to black spore masses; smut sori covered by a thin grayish membrane; characteristic foul smell; spores disperse at harvest.",
        "severity_range": (0.60, 0.95),
        "treatment": "Seed treatment with Carboxin 75% WP at 2g/kg seed or Thiram 75% WP at 3g/kg seed effectively controls smut. No curative treatment available for infected plants.",
        "chemicals": "Carboxin 75% WP (2g/kg seed), Thiram 75% DS (3g/kg), Tebuconazole 2% DS (1.5g/kg seed), Vitavax Power (2g/kg seed).",
        "fertilizers": "Optimize soil nutrition; apply lime if soil is acidic (pH below 6); potassium sulphate @ 60 kg/ha improves plant health.",
        "prevention": "Use certified smut-free seeds; treat seeds before sowing; practice 3-year crop rotation; destroy infected plants before spore dispersal; use smut-resistant varieties.",
        "dos": "Destroy infected plants before harvest; use clean seeds; bag infected heads before removal to prevent spore spread.",
        "donts": "Do not save seeds from infected fields; do not allow cattle to graze smut-infected fields; do not compost infected material."
    },
    "Bacterial Leaf Blight": {
        "description": "Bacterial leaf blight causes water-soaked streaks that turn brown, leading to significant foliage loss.",
        "symptoms": "Water-soaked linear streaks along the veins; exudation of bacterial ooze in early morning; bleaching of leaves.",
        "severity_range": (0.40, 0.80),
        "treatment": "Apply copper-based bactericides combined with antibiotics.",
        "chemicals": "Copper oxychloride (3g/L) + Streptocycline (0.1g/L).",
        "fertilizers": "Reduce nitrogen application during the active spread of the bacterium.",
        "prevention": "Use pathogen-free seed; ensure adequate field drainage.",
        "dos": "Rogue out infected plants; avoid field operations when leaves are wet.",
        "donts": "Do not use overhead irrigation."
    },
    "Helminthosporium Leaf Blight": {
        "description": "Helminthosporium leaf blight causes large necrotic areas, leading to defoliation under high humidity.",
        "symptoms": "Long, elliptical, grayish-brown to tan spots with yellow borders; coalescing to kill the entire leaf.",
        "severity_range": (0.50, 0.85),
        "treatment": "Use protective fungicides during the vegetative phase.",
        "chemicals": "Mancozeb (2.5g/L), Zineb 75% WP (2g/L).",
        "fertilizers": "Split nitrogen application to prevent lush, susceptible vegetative growth.",
        "prevention": "Use clean, treated seed. Choose resistant hybrids.",
        "dos": "Remove and burn crop debris after harvest.",
        "donts": "Avoid continuous millet cultivation in the same field."
    },
    "Shoot Fly Damage": {
        "description": "Shoot flies attack seedlings, causing 'dead heart' where the central shoot dries up.",
        "symptoms": "Central leaf whorl turns yellow, dries up, and can easily be pulled out (dead heart). Emits a foul smell from the base.",
        "severity_range": (0.30, 0.80),
        "treatment": "Apply granular insecticide in the soil at the time of sowing or early foliar spray.",
        "chemicals": "Carbofuran 3G at sowing, or foliar spray of Cypermethrin 10% EC (1ml/L).",
        "fertilizers": "Higher seed rate initially, followed by thinning.",
        "prevention": "Early sowing within 10-15 days of the onset of monsoon mitigates the attack.",
        "dos": "Remove and destroy the dead heart plants.",
        "donts": "Do not delay planting past the recommended season."
    },
    "Aphid Attack": {
        "description": "Aphids suck sap from tender plant parts, causing yellowing and a sticky honeydew that hosts sooty mold.",
        "symptoms": "Colonies of soft-bodied insects on undersides of leaves or panicles; yellowing of leaves; black sooty mold on honeydew.",
        "severity_range": (0.10, 0.60),
        "treatment": "Foliar application of systemic insecticides or neem oil.",
        "chemicals": "Dimethoate 30% EC (2ml/L), Neem oil 1500ppm (5ml/L).",
        "fertilizers": "Avoid excess nitrogen which promotes soft, succulent growth attractive to aphids.",
        "prevention": "Encourage natural enemies like ladybird beetles.",
        "dos": "Spray mostly directed towards the underside of leaves and panicles.",
        "donts": "Avoid broad-spectrum insecticides which kill beneficial predators."
    }
}

DISEASES = list(DISEASE_DB.keys())

def _get_severity(confidence: float, disease: str) -> str:
    """
    Rule-based severity calculation based on confidence and disease type.
    - Healthy -> Low
    - Confidence 0-50% -> Low
    - Confidence 51-80% -> Medium
    - Confidence >80% -> High
    """
    if disease == "Healthy":
        return "Low"
    
    conf_pct = confidence * 100
    if conf_pct <= 50:
        return "Low"
    elif conf_pct <= 80:
        return "Medium"
    else:
        return "High"

import json
import numpy as np

# ─────────────────────────────────────────────
# Dataset folder name → DISEASE_DB key mapping
# Translates the class names from ImageDataGenerator
# (which uses folder names) to the canonical keys in DISEASE_DB.
# ─────────────────────────────────────────────
CLASS_NAME_MAP = {
    # Exact folder names from dataset/ → DISEASE_DB keys
    "Aphid":             "Aphid Attack",
    "Bacterialblight":   "Bacterial Leaf Blight",
    "Black Rust":        "Rust",
    "Blast":             "Blast",
    "Brown Rust":        "Rust",
    "Healthy":           "Healthy",
    "Leaf Blight":       "Helminthosporium Leaf Blight",
    "Septoria":          "Leaf Spot",
    "Smut":              "Smut",
    "Stem fly":          "Shoot Fly Damage",
    "Tan spot":          "Leaf Spot",
    "downy_mildew":      "Downy Mildew",
    "rust":              "Rust",
    # From previous trainings (underscore-style names)
    "Aphid_Attack":              "Aphid Attack",
    "Bacterial_Leaf_Blight":     "Bacterial Leaf Blight",
    "Bacterial_Stripe":          "Bacterial Stripe",
    "Cercospora_Leaf_Spot":      "Cercospora Leaf Spot",
    "Helminthosporium_Leaf_Blight": "Helminthosporium Leaf Blight",
    "Leaf_Curl_Virus":           "Leaf Curl Virus",
    "Leaf_Spot":                 "Leaf Spot",
    "Mosaic_Disease":            "Mosaic Disease",
    "Grain_Mold":                "Grain Mold",
    "Nitrogen_Deficiency":       "Nitrogen Deficiency",
    "Potassium_Deficiency":      "Potassium Deficiency",
    "Shoot_Fly_Damage":          "Shoot Fly Damage",
    "Stem_Borer_Damage":         "Stem Borer Damage",
    "Zinc_Deficiency":           "Zinc Deficiency",
    "Anthracnose":               "Anthracnose",
    "Armyworm_Damage":           "Armyworm Damage",
    "Ergot":                     "Ergot",
    "blast":                     "Blast",
    "healthy":                   "Healthy",
    "downy mildew":              "Downy Mildew",
}

def _resolve_class_name(raw_label: str) -> str:
    """
    Map a raw class label (from class_names.json / folder name) to a
    canonical DISEASE_DB key.  Falls back to title-cased underscore-replace.
    """
    # 1. Exact match in map
    if raw_label in CLASS_NAME_MAP:
        return CLASS_NAME_MAP[raw_label]

    # 2. Case-insensitive match
    lower_map = {k.lower(): v for k, v in CLASS_NAME_MAP.items()}
    if raw_label.lower() in lower_map:
        return lower_map[raw_label.lower()]

    # 3. Fallback: replace underscores, title-case
    return raw_label.replace("_", " ").strip().title()

def get_disease_info(disease_name):
    # Normalise: replace underscores with spaces, strip, title-case
    friendly_name = disease_name.replace("_", " ").strip().title()

    # Direct lookup (preferred)
    if friendly_name in DISEASE_DB:
        return friendly_name, DISEASE_DB[friendly_name]

    # Case-insensitive fallback lookup
    lower_map = {k.lower(): k for k in DISEASE_DB}
    if friendly_name.lower() in lower_map:
        canonical = lower_map[friendly_name.lower()]
        return canonical, DISEASE_DB[canonical]

    # Generic fallback for unknown/new classes
    print(f"[WARNING] Disease '{friendly_name}' not found in DISEASE_DB – returning generic info.")
    return friendly_name, {
        "description":    f"This crop is affected by {friendly_name}, a common agricultural issue.",
        "symptoms":       f"Visible signs of {friendly_name} on leaves and stems.",
        "severity_range": (0.4, 0.8),
        "treatment":      "Consult local agricultural extension for specific fungicide or pesticide.",
        "chemicals":      "Broad-spectrum agricultural chemicals.",
        "fertilizers":    "Maintain balanced NPK to support crop recovery.",
        "prevention":     "Ensure good field sanitation, use resistant varieties.",
        "dos":            "Monitor crop health, remove affected parts early.",
        "donts":          "Do not ignore early symptoms, avoid working in wet fields."
    }

def _load_model_and_labels():
    """
    Lazy loader for the Keras model and class names.
    Ensures the model is loaded only ONCE and cached in memory.
    """
    global _MODEL, _CLASS_NAMES
    
    # Resolve paths relative to THIS file
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    model_path  = os.path.join(BASE_DIR, "model", "millet_disease_model.h5")
    labels_path = os.path.join(BASE_DIR, "model", "class_names.json")

    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL, _CLASS_NAMES

        if os.path.exists(model_path) and os.path.exists(labels_path):
            print(f"\n[BOOT] Loading Millet Disease Model into memory...")
            try:
                import tensorflow as tf
                # Suppress TF logs
                os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
                
                _MODEL = tf.keras.models.load_model(model_path)
                with open(labels_path, 'r') as f:
                    _CLASS_NAMES = json.load(f)
                
                print(f"[SUCCESS] Model loaded with {len(_CLASS_NAMES)} classes.")
                return _MODEL, _CLASS_NAMES
            except Exception as e:
                print(f"[ERROR] Failed to load model: {e}")
                return None, None
        else:
            print(f"[WARN] Model files not found at {model_path} or {labels_path}")
            return None, None

def predict_disease(image_path: str) -> dict:
    """
    Predict disease from an uploaded image using the trained CNN model.
    Uses a cached singleton model instance for performance.
    """
    print(f"\n[DEBUG] predict_disease() triggered for: {os.path.basename(image_path)}")

    try:
        # ── Validate uploaded image ──────────────────────────────────────────────────
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Uploaded image not found: {image_path}")

        img_pil = Image.open(image_path).convert('RGB')
        img_width, img_pil_height = img_pil.size

        # ── Get Model and Labels (Cached) ────────────────────────────────────────────
        model, class_names = _load_model_and_labels()

        if model is not None and class_names is not None:
            # ── Real CNN prediction ──────────────────────────────────────────────────
            # Preprocess: resize → numpy → normalize → add batch dim
            img_resized  = img_pil.resize((224, 224))
            img_array    = np.array(img_resized, dtype=np.float32) / 255.0
            img_array    = np.expand_dims(img_array, axis=0)          # (1, 224, 224, 3)

            predictions  = model.predict(img_array, verbose=0)
            pred_idx     = int(np.argmax(predictions[0]))
            raw_label    = class_names[pred_idx]
            confidence   = float(predictions[0][pred_idx])

            print(f"[DEBUG] Model prediction: '{raw_label}' (conf: {confidence:.4f})")

            # ── Normalise label to match DISEASE_DB keys ─────────────────────────────
            disease = _resolve_class_name(raw_label)
        else:
            # ── Deterministic mock fallback (no model file or load failure) ──────────
            print("[WARNING] Using deterministic mock prediction fallback.")
            with open(image_path, 'rb') as f:
                img_hash = hashlib.md5(f.read()).hexdigest()
            seed_val = int(img_hash[:8], 16)
            rng      = random.Random(seed_val)

            weights = [0.08, 0.18, 0.18, 0.18, 0.18, 0.20]
            disease  = rng.choices(DISEASES, weights=weights, k=1)[0]

            _, d_info = get_disease_info(disease)
            low, high  = d_info["severity_range"]
            confidence = rng.uniform(0.90, 0.99) if (low == 0.0 and high == 0.0) else rng.uniform(low, high)
            print(f"[DEBUG] Mock disease='{disease}', confidence={confidence:.4f}")

        # ── Look up disease details ──────────────────────────────────────────────────
        friendly_name, disease_info = get_disease_info(disease)
        severity = _get_severity(confidence, friendly_name)

        print(f"[DEBUG] Final → disease='{friendly_name}', confidence={confidence*100:.2f}%, severity='{severity}'")

        return {
            "success":      True,
            "disease_name": friendly_name,
            "description":  disease_info["description"],
            "symptoms":     disease_info["symptoms"],
            "confidence":   round(confidence * 100, 2),
            "severity":     severity,
            "treatment":    disease_info["treatment"],
            "chemicals":    disease_info["chemicals"],
            "fertilizers":  disease_info["fertilizers"],
            "prevention":   disease_info["prevention"],
            "dos":          disease_info["dos"],
            "donts":        disease_info["donts"],
            "image_size":   f"{img_width}x{img_pil_height}",
        }

    except FileNotFoundError as e:
        print(f"[ERROR] File not found: {e}")
        return {"success": False, "error": f"File not found: {e}",
                "disease_name": "Unknown", "confidence": 0, "severity": "Unknown"}

    except Exception as e:
        import traceback
        print(f"[ERROR] predict_disease failed: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e),
                "disease_name": "Unknown", "confidence": 0, "severity": "Unknown"}
