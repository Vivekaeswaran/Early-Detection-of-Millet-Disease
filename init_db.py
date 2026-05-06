"""Initialize database and seed demo data."""
from app import app, db
from models import User, ScanHistory, ExpertAdvice, FarmerQuery, Notification, ScrapeLog
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

DISEASE_NAMES = ["Downy Mildew", "Blast", "Rust", "Smut", "Ergot", "Healthy"]

with app.app_context():
    db.drop_all()
    db.create_all()
    print("✅ Database tables created.")

    # Admin
    admin = User(name="System Administrator", email="admin@millet.com",
                 password=generate_password_hash("admin123"),
                 role="admin", location="Chennai", language="en")
    db.session.add(admin)

    # Experts
    expert1 = User(name="Dr. Ramesh Kumar", email="expert@millet.com",
                   password=generate_password_hash("expert123"),
                   role="expert", location="Coimbatore", language="en")
    expert2 = User(name="Dr. Priya Sharma", email="priya@millet.com",
                   password=generate_password_hash("expert123"),
                   role="expert", location="Pune", language="hi")
    db.session.add_all([expert1, expert2])

    # Farmers
    locations = ["Madurai", "Trichy", "Salem", "Namakkal", "Erode", "Tiruvannamalai",
                 "Jodhpur", "Bikaner", "Jaipur", "Hyderabad"]
    crop_types = ["Pearl Millet", "Finger Millet", "Foxtail Millet", "Sorghum"]

    farmers = []
    farmer_names = [
        ("Ravi Kumar", "ravi@farm.com"), ("Murugan S", "murugan@farm.com"),
        ("Lakshmi D", "lakshmi@farm.com"), ("farmer@millet.com", "Karthik R"),
        ("Anand P", "anand@farm.com"), ("Selvam T", "selvam@farm.com"),
        ("Prabhu M", "prabhu@farm.com"), ("Meena R", "meena@farm.com"),
    ]

    # Demo farmer
    demo_farmer = User(name="Demo Farmer", email="farmer@millet.com",
                       password=generate_password_hash("farmer123"),
                       role="farmer", location=random.choice(locations),
                       crop_type="Pearl Millet", phone="9876543210", language="en")
    db.session.add(demo_farmer)
    db.session.flush()
    farmers.append(demo_farmer)

    for i in range(7):
        f = User(name=farmer_names[i][0] if i < len(farmer_names) else f"Farmer {i+1}",
                 email=farmer_names[i][1] if i < len(farmer_names) else f"farmer{i+1}@farm.com",
                 password=generate_password_hash("farmer123"),
                 role="farmer",
                 location=random.choice(locations),
                 crop_type=random.choice(crop_types),
                 language=random.choice(['en', 'ta', 'hi']))
        db.session.add(f)
        db.session.flush()
        farmers.append(f)

    db.session.flush()

    # Seed scan history
    disease_info = {
        "Downy Mildew": {"desc": "Fungal disease by Sclerospora graminicola.", "symptoms": "Yellow patches on leaves, white powder below leaves.",
                          "treatment": "Apply Metalaxyl 2.5g/kg seed."},
        "Blast": {"desc": "Fungal disease by Pyricularia grisea.", "symptoms": "Spindle-shaped lesions, neck rot.",
                  "treatment": "Spray Tricyclazole 0.6g/L."},
        "Rust": {"desc": "Disease by Puccinia substriata.", "symptoms": "Reddish-brown pustules on leaves.",
                 "treatment": "Apply Mancozeb 2.5 kg/ha."},
        "Smut": {"desc": "Covered kernel smut by Moesziomyces.", "symptoms": "Ear head replaced by black spores.",
                 "treatment": "Carboxin 75% WP seed treatment."},
        "Ergot": {"desc": "Caused by Claviceps fusiformis.", "symptoms": "Honeydew exudate from florets.",
                  "treatment": "No curative; use resistant varieties."},
        "Healthy": {"desc": "No disease detected.", "symptoms": "Normal green coloration.",
                    "treatment": "No treatment needed."},
    }

    severities = ["Low", "Medium", "High", "None"]
    scan_records = []
    for farmer_obj in farmers:
        num_scans = random.randint(2, 8)
        for j in range(num_scans):
            disease = random.choice(DISEASE_NAMES)
            conf = round(random.uniform(55.0, 97.0), 2)
            sev = "None" if disease == "Healthy" else random.choice(["Low", "Medium", "High"])
            days_ago = random.randint(1, 60)
            status = random.choice(['pending', 'verified', 'verified', 'pending'])
            s = ScanHistory(
                farmer_id=farmer_obj.id,
                image_path="uploads/sample_leaf.jpg",
                disease_name=disease,
                disease_description=disease_info[disease]["desc"],
                symptoms=disease_info[disease]["symptoms"],
                confidence=conf,
                severity=sev,
                treatment=disease_info[disease]["treatment"],
                chemicals="Mancozeb 75% WP",
                fertilizers="NPK 90:45:45 kg/ha",
                prevention="Use resistant varieties; practice crop rotation.",
                dos_donts="Do's: Use certified seeds; monitor weekly|||Don'ts: Don't over-irrigate; avoid excess nitrogen",
                status=status,
                expert_id=expert1.id if status == 'verified' else None,
                expert_notes="Verified by expert. Prediction is accurate." if status == 'verified' else None,
                verified_at=datetime.utcnow() - timedelta(days=days_ago-1) if status == 'verified' else None,
                scanned_at=datetime.utcnow() - timedelta(days=days_ago)
            )
            db.session.add(s)
            scan_records.append(s)

    db.session.flush()

    # Advice
    if farmers and scan_records:
        advice = ExpertAdvice(
            expert_id=expert1.id, farmer_id=farmers[0].id,
            scan_id=scan_records[0].id if scan_records else None,
            subject="Downy Mildew Control Measures",
            message="Dear farmer, I have reviewed your scan. Please apply Metalaxyl seed treatment immediately. Also ensure proper field drainage to prevent waterlogging which increases disease spread. Feel free to contact if you need more guidance.",
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.session.add(advice)

        query1 = FarmerQuery(
            farmer_id=farmers[0].id,
            subject="When to spray fungicide?",
            question="My millet crop shows yellow patches. When is the right time to spray fungicide and which one should I use?",
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        db.session.add(query1)

    # Notifications
    for farmer_obj in farmers[:3]:
        n = Notification(user_id=farmer_obj.id,
                         message="⚠️ High humidity forecast - risk of Downy Mildew. Consider preventive fungicide spray.",
                         type='warning', created_at=datetime.utcnow() - timedelta(hours=3))
        db.session.add(n)

    db.session.commit()
    print("✅ Demo data seeded successfully!")
    print("\n🔐 Demo Login Credentials:")
    print("  Admin  → admin@millet.com    / admin123")
    print("  Expert → expert@millet.com   / expert123")
    print("  Farmer → farmer@millet.com   / farmer123")
    print("\n🚀 Run the app with: python app.py")
    print("   Then visit: http://127.0.0.1:5000")
