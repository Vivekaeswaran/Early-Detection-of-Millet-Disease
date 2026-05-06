from models import db, ScanHistory

# Basic organic/chemical mapping based on disease category
FERTILIZER_KNOWLEDGE = {
    "Healthy": {
        "organic": "Apply 2-3 tons/acre of Farm Yard Manure (FYM) or Vermicompost. Include Neem cake (50 kg/acre) to maintain soil health.",
        "chemical": "Apply recommended basal NPK (80:40:40 kg/ha) in split doses. Top-dress with Urea at knee-high stage.",
        "notes": "Maintain balanced nutrition. Consider applying ZnSO4 @ 25 kg/ha if zinc deficiency is noticed."
    },
    "Blast": {
        "organic": "Apply Silica-rich organic amendments (e.g., rice husk ash) to strengthen cell walls. Use Jeevamrutham to boost soil microbes.",
        "chemical": "Reduce Nitrogen application. Apply Potassium (MOP @ 40 kg/ha) to improve disease resistance.",
        "notes": "Avoid excessive nitrogen as it makes plants succulent and highly susceptible to Blast."
    },
    "Downy Mildew": {
        "organic": "Apply Trichoderma viride enriched FYM (1 kg in 100 kg FYM) to soil before sowing.",
        "chemical": "Balanced NPK (90:45:45 kg/ha). Boost Potassium to enhance plant immunity.",
        "notes": "Ensure field has good drainage as waterlogging promotes downy mildew."
    },
    "Rust": {
        "organic": "Use composted poultry manure mixed with neem cake. Foliar spray of cow urine (10%) helps.",
        "chemical": "Apply Muriate of Potash (MOP) @ 60 kg/ha to improve rust resistance. Avoid late nitrogen sprays.",
        "notes": "Potassium plays a key role in reducing rust severity. Ensure sufficient K levels in soil."
    },
    "Smut": {
        "organic": "Apply well-decomposed organic manure. Avoid fresh cow dung as it may contain pathogens.",
        "chemical": "Apply Potassium Sulphate @ 60 kg/ha. Apply lime if soil pH is acidic (below 6.0).",
        "notes": "Ensure proper seed treatment before sowing; fertilizers cannot cure smut once the panicle is infected."
    },
    "Ergot": {
        "organic": "Use balanced FYM. Avoid nutrient stress during flowering.",
        "chemical": "Apply Boron @ 1.5 kg/ha as targeted soil application to improve pollination and reduce floret susceptibility.",
        "notes": "Proper fertilization ensures synchronous flowering, reducing the window of susceptibility to ergot."
    },
    "default": {
        "organic": "Apply standard Vermicompost or well-decomposed FYM (2 tons/acre) to improve soil structure and immunity.",
        "chemical": "Maintain balanced NPK ratio. Avoid excessive Nitrogen application during active disease spread.",
        "notes": "For most fungal/bacterial infections, reducing nitrogen and increasing potassium helps plant recovery."
    }
}

INSIGHTS_KNOWLEDGE = {
    "Healthy": [
        "Your crop is growing well. Maintain current irrigation schedule.",
        "Consider doing a routine weed check this week."
    ],
    "Blast": [
        "Blast spores spread rapidly in high humidity. Ensure good airflow.",
        "Isolate heavily infected plants if scattered to prevent windborne spread."
    ],
    "Downy Mildew": [
        "Waterlogging is the main trigger. Improve field drainage immediately.",
        "Avoid overhead irrigation which splashes spores onto healthy leaves."
    ],
    "Rust": [
        "Rust spreads via wind. Check downwind plants closely.",
        "Harvest early if crop is near maturity to avoid further yield loss."
    ],
    "Smut": [
        "Cover infected panicles with a bag before removing them to prevent spore dispersal.",
        "Do not allow cattle to graze on smut-infected fields."
    ],
    "Ergot": [
        "Ergot bodies are highly toxic. Hand-pick and destroy them before harvest.",
        "Ensure field equipment is thoroughly cleaned after working in this plot."
    ],
    "default": [
        "Monitor the infected area closely over the next 3-4 days.",
        "Remove and safely burn severely infected leaves to lower the pathogen load."
    ]
}

def get_fertilizer_recommendation(disease_name, severity):
    key = disease_name if disease_name in FERTILIZER_KNOWLEDGE else "default"
    data = FERTILIZER_KNOWLEDGE[key]
    
    # Adjust dose string based on severity
    notes = data["notes"]
    if severity == "High":
        notes += " IMMEDIATE ACTION REQUIRED: Suspend all nitrogenous fertilizers until the disease is controlled."
    elif severity == "Medium":
        notes += " Monitor crop response carefully. Apply fertilizers only after initial fungicide treatment."
        
    return {
        "organic": data["organic"],
        "chemical": data["chemical"],
        "notes": notes
    }

def get_precision_insights(disease_name, severity, location=None, history_count=0):
    key = disease_name if disease_name in INSIGHTS_KNOWLEDGE else "default"
    insights_list = INSIGHTS_KNOWLEDGE[key]
    
    # Formulate main insight text
    base_insight = insights_list[0]
    next_action = insights_list[1]
    
    insight_text = base_insight
    if location:
        insight_text += f" Based on localized weather patterns in {location}, ensure humidity is managed."
        
    if history_count > 2:
        insight_text += " WARNING: This field has a history of repeated infections. Consider crop rotation next season."
        
    if severity == "High":
        next_action = "URGENT: " + next_action
        
    return {
        "insight_text": insight_text,
        "next_action": next_action
    }

def calculate_effectiveness(prev_severity, curr_severity):
    """
    Returns (status, improvement_percent)
    Severity mapped to score: High: 3, Medium: 2, Low: 1, Healthy: 0
    """
    severity_map = {
        "High": 3,
        "Medium": 2,
        "Low": 1,
        "Healthy": 0
    }
    
    prev_score = severity_map.get(prev_severity, 3)
    curr_score = severity_map.get(curr_severity, 0)
    
    if curr_score < prev_score:
        status = "Improved"
        # Calculate percentage: difference / max_possible_difference(3)
        diff = prev_score - curr_score
        pct = int((diff / 3.0) * 100)
        # Ensure it's realistic (e.g., High -> Healthy is 100%)
        if prev_score > 0:
            pct = int((diff / prev_score) * 100)
    elif curr_score == prev_score:
        status = "No Change"
        pct = 0
    else:
        status = "Worsened"
        diff = curr_score - prev_score
        pct = -int((diff / 3.0) * 100)
        
    return status, pct

# ── Treatment Duration Knowledge Base ────────────────────────────────────────
# Each entry: (days_min, days_max, recheck_every_days)
TREATMENT_TRACKING_DAYS = {
    'Healthy':           (0,  0,  10),   # monitoring only
    'Blast':             (10, 14,  3),
    'Downy Mildew':      (7,  12,  3),
    'Rust':              (7,  10,  2),
    'Brown Rust':        (7,  10,  2),
    'Black Rust':        (7,  10,  2),
    'Smut':              (10, 14,  4),
    'Ergot':             (7,  10,  3),
    'Leaf Spot':         (5,   7,  2),
    'Leaf Blight':       (5,   7,  2),
    'Aphid':             (3,   5,  2),
    'Bacterialblight':   (5,   7,  3),
    'Septoria':          (7,   9,  3),
    'Stem fly':          (3,   5,  2),
    'Tan spot':          (5,   7,  2),
    'downy_mildew':      (7,  12,  3),   # alias
}
# Friendly label for how long to track, shown on scan result
TREATMENT_LABEL = {
    'Healthy':        'No treatment tracking needed. Monitor weekly.',
    'Blast':          'Track for 10–14 days. Recheck every 3 days.',
    'Downy Mildew':   'Track for 7–12 days. Recheck every 3 days.',
    'Rust':           'Track for 7–10 days. Recheck every 2 days.',
    'Brown Rust':     'Track for 7–10 days. Recheck every 2 days.',
    'Black Rust':     'Track for 7–10 days. Recheck every 2 days.',
    'Smut':           'Track for 10–14 days. Recheck every 4 days.',
    'Ergot':          'Track for 7–10 days. Recheck every 3 days.',
    'Leaf Spot':      'Track for 5–7 days. Recheck every 2 days.',
    'Leaf Blight':    'Track for 5–7 days. Recheck every 2 days.',
    'Aphid':          'Track for 3–5 days. Recheck every 2 days.',
    'Bacterialblight':'Track for 5–7 days. Recheck every 3 days.',
    'Septoria':       'Track for 7–9 days. Recheck every 3 days.',
    'Stem fly':       'Track for 3–5 days. Recheck every 2 days.',
    'Tan spot':       'Track for 5–7 days. Recheck every 2 days.',
}
_DEFAULT_TRACK = (5, 7, 3)

def get_treatment_plan_info(disease_name):
    """
    Returns dict:
      min_days, max_days, suggested_days (avg), recheck_days,
      label (human-readable string), next_recheck_date, end_date
    """
    from datetime import datetime, timedelta
    key_lower = {k.lower(): v for k, v in TREATMENT_TRACKING_DAYS.items()}
    mn, mx, recheck = key_lower.get(disease_name.lower(), _DEFAULT_TRACK)
    suggested = (mn + mx) // 2
    now = datetime.utcnow()
    label_lower = {k.lower(): v for k, v in TREATMENT_LABEL.items()}
    label = label_lower.get(disease_name.lower(),
                            f'Track for {mn}–{mx} days. Recheck every {recheck} days.')
    return {
        'days_min':         mn,
        'days_max':         mx,
        'suggested_days':   suggested,
        'recheck_days':     recheck,
        'label':            label,
        'next_recheck_date': now + timedelta(days=recheck),
        'end_date':          now + timedelta(days=suggested),
    }


# Keep legacy name for backward compatibility in farmer.py
FOLLOW_UP_MAPPING = {k: v[0] for k, v in TREATMENT_TRACKING_DAYS.items()}

def get_treatment_followup(disease_name):
    """Legacy helper — returns (follow_up_days, follow_up_date)."""
    from datetime import datetime, timedelta
    info = get_treatment_plan_info(disease_name)
    days = info['suggested_days'] or 5
    return days, datetime.utcnow() + timedelta(days=days)


# ── Smart Suggestions ────────────────────────────────────────────────────────
def get_smart_suggestions(disease_name, recovery_status, days_remaining):
    """Return a list of smart suggestion strings for the Track Treatment page."""
    sug = []
    if recovery_status == 'Improved':
        sug.append('Great progress! Continue the current treatment plan.')
        sug.append('Upload a new image every 2–3 days to confirm recovery.')
    elif recovery_status == 'Worsened':
        sug.append('⚠ Condition has worsened. Contact an expert immediately.')
        sug.append('Review your fungicide/chemical application frequency.')
    else:
        sug.append('No major change detected. Continue treatment consistently.')
        sug.append('Ensure spray coverage reaches both sides of the leaf.')

    if days_remaining > 0:
        sug.append(f'Continue treatment for {days_remaining} more day(s).')
    else:
        sug.append('Treatment duration complete. Do a final scan to confirm recovery.')

    sug.append('Maintain proper watering — avoid over-irrigation.')
    sug.append('If no improvement in 3–4 days, consult your agricultural expert.')
    return sug