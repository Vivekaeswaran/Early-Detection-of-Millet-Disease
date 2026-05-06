from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_required, current_user
from datetime import datetime
from models import db, User, ScanHistory, ExpertAdvice, FarmerQuery, Notification

expert = Blueprint('expert', __name__, url_prefix='/expert')

def expert_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'expert':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.expert_login'))
        return f(*args, **kwargs)
    return decorated

@expert.route('/dashboard')
@login_required
@expert_required
def dashboard():
    pending_count = ScanHistory.query.filter_by(status='pending').count()
    verified_count = ScanHistory.query.filter_by(status='verified').count()
    open_queries = FarmerQuery.query.filter_by(status='open').count()
    recent_pending = ScanHistory.query.filter_by(status='pending')\
                                      .order_by(ScanHistory.scanned_at.desc()).limit(5).all()
    return render_template('expert/dashboard.html',
                           pending_count=pending_count, verified_count=verified_count,
                           open_queries=open_queries, recent_pending=recent_pending)

@expert.route('/pending-cases')
@login_required
@expert_required
def pending_cases():
    page = request.args.get('page', 1, type=int)
    cases = ScanHistory.query.filter_by(status='pending')\
                             .order_by(ScanHistory.scanned_at.desc())\
                             .paginate(page=page, per_page=10, error_out=False)
    return render_template('expert/pending_cases.html', cases=cases)

@expert.route('/verified-cases')
@login_required
@expert_required
def verified_cases():
    page = request.args.get('page', 1, type=int)
    cases = ScanHistory.query.filter_by(status='verified')\
                             .order_by(ScanHistory.verified_at.desc())\
                             .paginate(page=page, per_page=10, error_out=False)
    return render_template('expert/verified_cases.html', cases=cases)

@expert.route('/verify/<int:scan_id>', methods=['GET', 'POST'])
@login_required
@expert_required
def verify_case(scan_id):
    scan = ScanHistory.query.get_or_404(scan_id)
    if request.method == 'POST':
        corrected_disease = request.form.get('corrected_disease', scan.disease_name).strip()
        severity = request.form.get('severity', scan.severity)
        expert_notes = request.form.get('expert_notes', '').strip()
        treatment = request.form.get('treatment', scan.treatment).strip()
        prevention = request.form.get('prevention', scan.prevention).strip()
        symptoms = request.form.get('symptoms', scan.symptoms).strip()
        fertilizers = request.form.get('fertilizers', scan.fertilizers).strip()

        scan.disease_name = corrected_disease
        scan.severity = severity
        scan.expert_notes = expert_notes
        scan.treatment = treatment
        scan.prevention = prevention
        scan.symptoms = symptoms
        scan.fertilizers = fertilizers
        scan.status = 'verified'
        scan.expert_id = current_user.id
        scan.verified_at = datetime.utcnow()
        db.session.commit()

        # Notify farmer
        notif = Notification(
            user_id=scan.farmer_id,
            message=f"Your scan #{scan.id} has been verified by an expert. Disease: {corrected_disease} ({severity} severity).",
            type='success'
        )
        db.session.add(notif)
        db.session.commit()

        flash(f'Case #{scan_id} verified successfully!', 'success')
        return redirect(url_for('expert.pending_cases'))

    from ml_model import DISEASES
    return render_template('expert/verify_case.html', scan=scan, diseases=DISEASES)

@expert.route('/send-advice', methods=['GET', 'POST'])
@login_required
@expert_required
def send_advice():
    if request.method == 'POST':
        farmer_id = request.form.get('farmer_id', type=int)
        scan_id = request.form.get('scan_id', type=int)
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()

        farmer = User.query.filter_by(id=farmer_id, role='farmer').first()
        if not farmer:
            flash('Farmer not found.', 'danger')
            return redirect(url_for('expert.send_advice'))

        advice = ExpertAdvice(expert_id=current_user.id, farmer_id=farmer_id,
                               scan_id=scan_id or None, subject=subject, message=message)
        db.session.add(advice)

        notif = Notification(user_id=farmer_id,
                             message=f"New advice from expert {current_user.name}: {subject}",
                             type='info')
        db.session.add(notif)
        db.session.commit()

        flash('Advice sent to farmer successfully!', 'success')
        return redirect(url_for('expert.dashboard'))

    farmers = User.query.filter_by(role='farmer', is_blocked=False).all()
    return render_template('expert/send_advice.html', farmers=farmers)

@expert.route('/queries')
@login_required
@expert_required
def queries():
    page = request.args.get('page', 1, type=int)
    queries_list = FarmerQuery.query.order_by(FarmerQuery.created_at.desc())\
                                    .paginate(page=page, per_page=10, error_out=False)
    return render_template('expert/queries.html', queries=queries_list)

@expert.route('/answer-query/<int:query_id>', methods=['POST'])
@login_required
@expert_required
def answer_query(query_id):
    q = FarmerQuery.query.get_or_404(query_id)
    answer = request.form.get('answer', '').strip()
    if answer:
        q.answer = answer
        q.answered_by = current_user.id
        q.status = 'answered'
        q.answered_at = datetime.utcnow()
        db.session.commit()

        notif = Notification(user_id=q.farmer_id,
                             message=f"Your query '{q.subject}' has been answered by an expert!",
                             type='success')
        db.session.add(notif)
        db.session.commit()
        flash('Answer submitted successfully!', 'success')
    return redirect(url_for('expert.queries'))
