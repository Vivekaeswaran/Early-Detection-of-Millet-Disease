from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone, timedelta

# Indian Standard Time offset (UTC+5:30)
_IST = timezone(timedelta(hours=5, minutes=30))

def _now_ist():
    """Return the current datetime in IST (no pytz dependency needed)."""
    return datetime.now(_IST).replace(tzinfo=None)  # store as naive IST in SQLite


db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=True) # Added for faculty demo
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # farmer, expert, admin
    location = db.Column(db.String(100))
    crop_type = db.Column(db.String(100))
    language = db.Column(db.String(20), default='en')
    phone = db.Column(db.String(20))
    status = db.Column(db.String(50), default='Active') # Added for faculty demo
    is_active = db.Column(db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scans = db.relationship('ScanHistory', backref='farmer', lazy=True,
                            foreign_keys='ScanHistory.farmer_id')
    queries = db.relationship('FarmerQuery', backref='farmer', lazy=True,
                              foreign_keys='FarmerQuery.farmer_id')


class ScanHistory(db.Model):
    __tablename__ = 'scan_history'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(300), nullable=False)
    disease_name = db.Column(db.String(150))
    disease_description = db.Column(db.Text)
    symptoms = db.Column(db.Text)
    confidence = db.Column(db.Float)
    severity = db.Column(db.String(20))  # Low, Medium, High
    treatment = db.Column(db.Text)
    chemicals = db.Column(db.Text)
    fertilizers = db.Column(db.Text)
    prevention = db.Column(db.Text)
    dos_donts = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')  # pending, verified
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    expert_notes = db.Column(db.Text)
    verified_at = db.Column(db.DateTime)
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_days = db.Column(db.Integer, default=0)
    next_follow_up_date = db.Column(db.DateTime)

    expert = db.relationship('User', foreign_keys=[expert_id])


class ExpertAdvice(db.Model):
    __tablename__ = 'expert_advice'
    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan_history.id'), nullable=True)
    subject = db.Column(db.String(200))
    disease_name = db.Column(db.String(150))
    symptoms = db.Column(db.Text)
    treatment = db.Column(db.Text)
    fertilizer_suggestion = db.Column(db.Text)
    prevention_methods = db.Column(db.Text)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expert = db.relationship('User', foreign_keys=[expert_id])
    farmer = db.relationship('User', foreign_keys=[farmer_id])
    scan = db.relationship('ScanHistory', foreign_keys=[scan_id])


class FarmerQuery(db.Model):
    __tablename__ = 'farmer_queries'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200))
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    answered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    status = db.Column(db.String(20), default='open')  # open, answered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime)

    expert = db.relationship('User', foreign_keys=[answered_by])


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='info')  # info, warning, success
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ScrapeLog(db.Model):
    __tablename__ = 'scrape_logs'
    id = db.Column(db.Integer, primary_key=True)
    disease_class = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    local_path = db.Column(db.String(300))
    status = db.Column(db.String(50), default='downloaded')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class FertilizerRecommendation(db.Model):
    __tablename__ = 'fertilizer_recommendations'
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan_history.id'), nullable=False)
    disease_name = db.Column(db.String(150))
    severity_level = db.Column(db.String(20))
    organic_option = db.Column(db.Text)
    chemical_option = db.Column(db.Text)
    usage_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    scan = db.relationship('ScanHistory', foreign_keys=[scan_id])


class PrecisionInsight(db.Model):
    __tablename__ = 'precision_insights'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan_history.id'), nullable=False)
    disease_name = db.Column(db.String(150))
    severity_level = db.Column(db.String(20))
    insight_text = db.Column(db.Text)
    next_action = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    scan = db.relationship('ScanHistory', foreign_keys=[scan_id])


class TreatmentTracking(db.Model):
    __tablename__ = 'treatment_tracking'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    previous_history_id = db.Column(db.Integer, db.ForeignKey('scan_history.id'), nullable=False)
    followup_image_path = db.Column(db.String(300))
    previous_severity = db.Column(db.String(20))
    current_severity = db.Column(db.String(20))
    effectiveness_status = db.Column(db.String(50))
    improvement_percent = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    previous_scan = db.relationship('ScanHistory', foreign_keys=[previous_history_id])


class TreatmentPlan(db.Model):
    """Full treatment plan created right after first disease detection."""
    __tablename__ = 'treatment_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scan_id = db.Column(db.Integer, db.ForeignKey('scan_history.id'), nullable=False)
    disease_name = db.Column(db.String(150))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    suggested_days = db.Column(db.Integer, default=7)
    days_min = db.Column(db.Integer, default=7)
    days_max = db.Column(db.Integer, default=10)
    days_completed = db.Column(db.Integer, default=0)
    previous_severity = db.Column(db.String(20))
    current_severity = db.Column(db.String(20))
    recovery_status = db.Column(db.String(50), default='In Progress')
    recovery_percentage = db.Column(db.Integer, default=0)
    next_recheck_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])
    scan = db.relationship('ScanHistory', foreign_keys=[scan_id])
    redetections = db.relationship('RedetectionHistory', backref='plan', lazy=True,
                                   foreign_keys='RedetectionHistory.plan_id')


class RedetectionHistory(db.Model):
    """Every re-upload/recheck result during treatment tracking."""
    __tablename__ = 'redetection_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('treatment_plans.id'), nullable=False)
    previous_disease = db.Column(db.String(150))
    current_disease = db.Column(db.String(150))
    previous_severity = db.Column(db.String(20))
    current_severity = db.Column(db.String(20))
    improvement_status = db.Column(db.String(50))   # Improved / No Change / Worsened
    recovery_percentage = db.Column(db.Integer, default=0)
    image_path = db.Column(db.String(300))
    confidence = db.Column(db.Float)
    notes = db.Column(db.Text)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

class SensorData(db.Model):
    __tablename__ = 'sensor_data'
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    soil_moisture = db.Column(db.Float) # Legacy
    soil_moisture_raw = db.Column(db.Integer)
    soil_moisture_percent = db.Column(db.Float)
    status = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=_now_ist)  # stored as IST


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    image_path = db.Column(db.String(300))
    disease_name = db.Column(db.String(150))
    confidence_score = db.Column(db.Float)
    severity_level = db.Column(db.String(20))
    report_path = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

