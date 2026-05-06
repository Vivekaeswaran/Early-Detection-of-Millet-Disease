from app import app
from models import db, FertilizerRecommendation, PrecisionInsight, TreatmentTracking

with app.app_context():
    db.create_all()
    print("Database tables created successfully!")
