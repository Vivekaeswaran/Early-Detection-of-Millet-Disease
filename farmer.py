import os
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, send_from_directory, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from models import (db, User, ScanHistory, ExpertAdvice, FarmerQuery, Notification,
                    FertilizerRecommendation, PrecisionInsight, TreatmentTracking,
                    TreatmentPlan, RedetectionHistory, SensorData, Report)

from ml_model import predict_disease
from pdf_report import generate_pdf_report
from utils import CROP_TIPS, WEATHER_WARNINGS
from features import (get_fertilizer_recommendation, get_precision_insights,
                       calculate_effectiveness, get_treatment_plan_info,
                       get_smart_suggestions)
import random

farmer = Blueprint('farmer', __name__, url_prefix='/farmer')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def farmer_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'farmer':
            flash('Access denied.', 'danger')
            return redirect(url_for('auth.farmer_login'))
        return f(*args, **kwargs)
    return decorated

@farmer.route('/dashboard')
@login_required
@farmer_required
def dashboard():
    total_scans = ScanHistory.query.filter_by(farmer_id=current_user.id).count()
    recent_scans = ScanHistory.query.filter_by(farmer_id=current_user.id)\
                                    .order_by(ScanHistory.scanned_at.desc()).limit(5).all()
    unread_advice = ExpertAdvice.query.filter_by(farmer_id=current_user.id, is_read=False).count()
    open_queries = FarmerQuery.query.filter_by(farmer_id=current_user.id, status='open').count()
    tip = random.choice(CROP_TIPS)
    weather_warning = WEATHER_WARNINGS['normal']
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                                      .order_by(Notification.created_at.desc()).limit(5).all()
    
    # Fetch latest sensor data
    latest_sensor = SensorData.query.order_by(SensorData.created_at.desc()).first()
    
    return render_template('farmer/dashboard.html',
                           total_scans=total_scans,
                           recent_scans=recent_scans, unread_advice=unread_advice,
                           open_queries=open_queries, tip=tip,
                           weather_warning=weather_warning,
                           notifications=notifications,
                           latest_sensor=latest_sensor)


@farmer.route('/scan', methods=['GET', 'POST'])
@login_required
@farmer_required
def scan():
    result = None
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('No image uploaded.', 'warning')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('No image selected.', 'warning')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(f"{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            filepath = os.path.abspath(os.path.join(upload_dir, filename))  # always absolute
            file.save(filepath)
            current_app.logger.info(f"[SCAN] Image saved to: {filepath}")

            prediction = predict_disease(filepath)

            if prediction['success']:
                from features import get_treatment_followup
                f_days, f_date = get_treatment_followup(prediction['disease_name'])

                dos_donts_str = f"Do's: {prediction['dos']}|||Don'ts: {prediction['donts']}"
                scan_record = ScanHistory(
                    farmer_id=current_user.id,
                    image_path=f"uploads/{filename}",
                    disease_name=prediction['disease_name'],
                    disease_description=prediction['description'],
                    symptoms=prediction['symptoms'],
                    confidence=prediction['confidence'],
                    severity=prediction['severity'],
                    treatment=prediction['treatment'],
                    chemicals=prediction['chemicals'],
                    fertilizers=prediction['fertilizers'],
                    prevention=prediction['prevention'],
                    dos_donts=dos_donts_str,
                    status='pending',
                    follow_up_days=f_days,
                    next_follow_up_date=f_date
                )
                db.session.add(scan_record)
                db.session.commit()

                # ── Create Treatment Plan for this scan ──────────────────────
                plan = None
                if prediction['disease_name'] != 'Healthy':
                    tinfo = get_treatment_plan_info(prediction['disease_name'])
                    plan = TreatmentPlan(
                        user_id=current_user.id,
                        scan_id=scan_record.id,
                        disease_name=prediction['disease_name'],
                        suggested_days=tinfo['suggested_days'],
                        days_min=tinfo['days_min'],
                        days_max=tinfo['days_max'],
                        previous_severity=prediction['severity'],
                        current_severity=prediction['severity'],
                        next_recheck_date=tinfo['next_recheck_date'],
                        notes=tinfo['label'],
                    )
                    db.session.add(plan)
                    db.session.flush()   # get plan.id before commit

                notif = Notification(user_id=current_user.id,
                                     message=f"Disease detected: {prediction['disease_name']} ({prediction['severity']} severity). Check your scan history.",
                                     type='warning' if prediction['severity'] in ['High', 'Medium'] else 'success')
                db.session.add(notif)
                
                # --- NEW LOGIC: Generate and save Smart Fertilizer & Precision Insights ---
                fert_data = get_fertilizer_recommendation(prediction['disease_name'], prediction['severity'])
                fert_record = FertilizerRecommendation(
                    scan_id=scan_record.id,
                    disease_name=prediction['disease_name'],
                    severity_level=prediction['severity'],
                    organic_option=fert_data['organic'],
                    chemical_option=fert_data['chemical'],
                    usage_notes=fert_data['notes']
                )
                db.session.add(fert_record)
                
                hist_count = ScanHistory.query.filter_by(farmer_id=current_user.id, disease_name=prediction['disease_name']).count()
                insight_data = get_precision_insights(prediction['disease_name'], prediction['severity'], current_user.location, hist_count)
                insight_record = PrecisionInsight(
                    user_id=current_user.id,
                    scan_id=scan_record.id,
                    disease_name=prediction['disease_name'],
                    severity_level=prediction['severity'],
                    insight_text=insight_data['insight_text'],
                    next_action=insight_data['next_action']
                )
                db.session.add(insight_record)
                db.session.commit()

                result = {
                    **prediction, 
                    'scan_id': scan_record.id, 
                    'image_filename': filename,
                    'fertilizer': fert_record,
                    'insight': insight_record,
                    'follow_up_days': f_days,
                    'next_follow_up_date': f_date.strftime('%Y-%m-%d'),
                    'treatment_plan_info': get_treatment_plan_info(prediction['disease_name']),
                    'plan_id': plan.id if plan else None,
                }
                current_app.logger.info(f"[SCAN] Successfully detected {prediction['disease_name']} with {prediction['confidence']}% confidence.")
            else:
                err_msg = prediction.get('error', 'Unknown AI error')
                trace = prediction.get('traceback', 'No traceback available')
                current_app.logger.error(f"[SCAN] Prediction failed for {filename}: {err_msg}")
                flash(f"⚠️ Disease detection failed. (Detail: {err_msg})", 'danger')
        else:
            flash('Invalid file type. Please upload a valid image.', 'danger')
    return render_template('farmer/scan.html', result=result)

@farmer.route('/history')
@login_required
@farmer_required
def history():
    page = request.args.get('page', 1, type=int)
    scans = ScanHistory.query.filter_by(farmer_id=current_user.id)\
                             .order_by(ScanHistory.scanned_at.desc())\
                             .paginate(page=page, per_page=8, error_out=False)
    return render_template('farmer/history.html', scans=scans)

@farmer.route('/report/<int:scan_id>')
@login_required
@farmer_required
def download_report(scan_id):
    scan = ScanHistory.query.filter_by(id=scan_id, farmer_id=current_user.id).first_or_404()
    try:
        filename = generate_pdf_report(scan, current_user)
        reports_dir = os.path.join(current_app.root_path, 'static', 'reports')
        
        # Store report metadata in database
        report_record = Report(
            farmer_id=current_user.id,
            image_path=scan.image_path,
            disease_name=scan.disease_name,
            confidence_score=scan.confidence,
            severity_level=scan.severity,
            report_path=f"static/reports/{filename}"
        )
        db.session.add(report_record)
        db.session.commit()
        
        return send_from_directory(reports_dir, filename, as_attachment=True)
    except Exception as e:
        flash(f'Report generation failed: {str(e)}', 'danger')
        return redirect(url_for('farmer.history'))

@farmer.route('/advice')
@login_required
@farmer_required
def advice():
    advices = ExpertAdvice.query.filter_by(farmer_id=current_user.id)\
                                .order_by(ExpertAdvice.created_at.desc()).all()
    # Mark as read
    for a in advices:
        if not a.is_read:
            a.is_read = True
    db.session.commit()
    return render_template('farmer/advice.html', advices=advices)

@farmer.route('/query', methods=['GET', 'POST'])
@login_required
@farmer_required
def query():
    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        question = request.form.get('question', '').strip()
        if question:
            q = FarmerQuery(farmer_id=current_user.id, subject=subject, question=question)
            db.session.add(q)
            db.session.commit()
            flash('Your query has been submitted to the experts!', 'success')
            return redirect(url_for('farmer.query'))
    queries = FarmerQuery.query.filter_by(farmer_id=current_user.id)\
                               .order_by(FarmerQuery.created_at.desc()).all()
    return render_template('farmer/query.html', queries=queries)

@farmer.route('/treatments')
@login_required
@farmer_required
def treatments():
    """List all active treatment plans for this farmer."""
    plans = TreatmentPlan.query.filter_by(user_id=current_user.id)\
                                .order_by(TreatmentPlan.created_at.desc()).all()
    # Compute days_completed & remaining on the fly
    now = datetime.utcnow()
    for p in plans:
        p.days_completed = max(0, (now - p.start_date).days)
        p.remaining_days = max(0, p.suggested_days - p.days_completed)
        pct = min(100, int(p.days_completed / max(p.suggested_days, 1) * 100))
        p.timeline_pct = pct
        if p.days_completed >= p.suggested_days and p.recovery_status == 'In Progress':
            p.recovery_status = 'Complete'
    return render_template('farmer/treatments.html', plans=plans)

@farmer.route('/track/<int:plan_id>', methods=['GET', 'POST'])
@login_required
@farmer_required
def track_treatment(plan_id):
    """View a treatment plan and optionally re-upload a leaf image for re-detection."""
    plan = TreatmentPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    scan = plan.scan

    now = datetime.utcnow()
    plan.days_completed = max(0, (now - plan.start_date).days)
    plan.remaining_days = max(0, plan.suggested_days - plan.days_completed)
    plan.timeline_pct   = min(100, int(plan.days_completed / max(plan.suggested_days, 1) * 100))

    redetections = RedetectionHistory.query.filter_by(plan_id=plan.id)\
                                           .order_by(RedetectionHistory.checked_at.desc()).all()

    redetect_result = None

    if request.method == 'POST':
        if 'recheck_image' not in request.files or request.files['recheck_image'].filename == '':
            flash('Please select an image to re-check.', 'warning')
            return redirect(request.url)

        file = request.files['recheck_image']
        if file and allowed_file(file.filename):
            fname = secure_filename(
                f"recheck_{current_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            )
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            fpath = os.path.join(upload_dir, fname)
            file.save(fpath)

            # ── Run AI prediction on the new image ──────────────────────────
            prediction = predict_disease(fpath)
            if not prediction['success']:
                flash(f"Re-detection failed: {prediction.get('error', 'Unknown error')}", 'danger')
                return redirect(request.url)

            curr_disease  = prediction['disease_name']
            curr_severity = prediction['severity']
            curr_conf     = prediction['confidence']

            status, pct = calculate_effectiveness(plan.current_severity, curr_severity)

            # ── Save to RedetectionHistory ──────────────────────────────────
            rh = RedetectionHistory(
                user_id         = current_user.id,
                plan_id         = plan.id,
                previous_disease= plan.disease_name,
                current_disease = curr_disease,
                previous_severity=plan.current_severity,
                current_severity= curr_severity,
                improvement_status=status,
                recovery_percentage=max(pct, 0),
                image_path      = f'uploads/{fname}',
                confidence      = curr_conf,
            )
            db.session.add(rh)

            # ── Update the plan ────────────────────────────────────────────
            plan.current_severity    = curr_severity
            plan.recovery_status     = status
            plan.recovery_percentage = max(pct, 0)
            plan.next_recheck_date   = now + timedelta(days=3)
            plan.updated_at          = now
            db.session.commit()

            suggestions = get_smart_suggestions(curr_disease, status, plan.remaining_days)

            redetect_result = {
                'prediction':     prediction,
                'previous_disease': plan.disease_name,
                'curr_disease':   curr_disease,
                'prev_severity':  rh.previous_severity,
                'curr_severity':  curr_severity,
                'status':         status,
                'pct':            max(pct, 0),
                'image_path':     f'uploads/{fname}',
                'confidence':     curr_conf,
                'suggestions':    suggestions,
            }
            flash(f'Re-check complete! Result: {status}', 'success')
        else:
            flash('Invalid file type.', 'danger')

    suggestions = get_smart_suggestions(
        plan.disease_name,
        plan.recovery_status,
        plan.remaining_days if hasattr(plan, 'remaining_days') else 0
    )

    return render_template('farmer/treatment_track.html',
                           plan=plan,
                           scan=scan,
                           redetections=redetections,
                           redetect_result=redetect_result,
                           suggestions=suggestions)


@farmer.route('/hardware')
@login_required
@farmer_required
def hardware():
    """Live sensor data monitor — reads from DB only."""
    latest = SensorData.query.order_by(SensorData.created_at.desc()).first()
    history = SensorData.query.order_by(SensorData.created_at.desc()).limit(20).all()
    return render_template('farmer/hardware.html', latest=latest, history=history)


@farmer.route('/reports-list')
@login_required
@farmer_required
def reports_list():
    """Show all PDF reports generated for this farmer."""
    from models import Report
    reports = Report.query.filter_by(farmer_id=current_user.id)\
                          .order_by(Report.created_at.desc()).all()
    return render_template('farmer/reports.html', reports=reports)
