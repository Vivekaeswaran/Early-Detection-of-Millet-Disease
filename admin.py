from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, make_response, session
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from models import db, User, ScanHistory, ExpertAdvice, FarmerQuery, Notification, ScrapeLog
import json
import threading
import subprocess
import os
from data_pipeline import run_pipeline

admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_farmers = User.query.filter_by(role='farmer').count()
    total_experts = User.query.filter_by(role='expert').count()
    total_scans = ScanHistory.query.count()
    pending_scans = ScanHistory.query.filter_by(status='pending').count()
    verified_scans = ScanHistory.query.filter_by(status='verified').count()
    open_queries = FarmerQuery.query.filter_by(status='open').count()
    recent_scans = ScanHistory.query.order_by(ScanHistory.scanned_at.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_farmers=total_farmers, total_experts=total_experts,
                           total_scans=total_scans, pending_scans=pending_scans,
                           verified_scans=verified_scans, open_queries=open_queries,
                           recent_scans=recent_scans)

@admin.route('/users')
@login_required
@admin_required
def users():
    role_filter = request.args.get('role', 'farmer')
    page = request.args.get('page', 1, type=int)
    users_list = User.query.filter_by(role=role_filter)\
                           .order_by(User.created_at.desc())\
                           .paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/users.html', users=users_list, role_filter=role_filter)

@admin.route('/toggle-block/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_block(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    db.session.commit()
    status = 'blocked' if user.is_blocked else 'unblocked'
    flash(f'User {user.name} has been {status}.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot delete an admin account.', 'danger')
        return redirect(url_for('admin.users'))
    db.session.delete(user)
    db.session.commit()
    flash(f'User {user.name} deleted.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/add-expert', methods=['GET', 'POST'])
@login_required
@admin_required
def add_expert():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'warning')
            return redirect(url_for('admin.add_expert'))
        expert = User(name=name, email=email, password=generate_password_hash(password),
                      role='expert')
        db.session.add(expert)
        db.session.commit()
        flash(f'Expert {name} added successfully!', 'success')
        return redirect(url_for('admin.users', role='expert'))
    return render_template('admin/add_expert.html')

@admin.route('/send-notification', methods=['POST'])
@login_required
@admin_required
def send_notification():
    target = request.form.get('target', 'all')
    message = request.form.get('message', '').strip()
    notif_type = request.form.get('type', 'info')
    if not message:
        flash('Message cannot be empty.', 'warning')
        return redirect(url_for('admin.dashboard'))
    if target == 'all':
        farmers = User.query.filter_by(role='farmer', is_blocked=False).all()
        for f in farmers:
            n = Notification(user_id=f.id, message=message, type=notif_type)
            db.session.add(n)
    db.session.commit()
    flash(f'Notification sent to {target} users!', 'success')
    return redirect(url_for('admin.dashboard'))

@admin.route('/all-scans')
@login_required
@admin_required
def all_scans():
    page = request.args.get('page', 1, type=int)
    scans = ScanHistory.query.order_by(ScanHistory.scanned_at.desc())\
                             .paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/all_scans.html', scans=scans)

@admin.route('/trigger-retrain', methods=['POST'])
@login_required
@admin_required
def trigger_retrain():
    def retrain_task():
        try:
            print("Starting data pipeline...")
            run_pipeline(limit_per_class=10)
            print("Data pipeline finished. Starting training...")
            train_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'train_model.py')
            # --force ensures retraining even if model file already exists
            subprocess.run(["python", train_script, "--force"], check=True)
            print("Training finished.")
        except Exception as e:
            print(f"Error in retrain task: {e}")

    thread = threading.Thread(target=retrain_task)
    thread.start()

    flash('Model retraining started in the background. Check Admin → Model Metrics once complete.', 'info')
    return redirect(url_for('admin.dataset_management'))



@admin.route('/dataset-management')
@login_required
@admin_required
def dataset_management():
    page = request.args.get('page', 1, type=int)
    logs = ScrapeLog.query.order_by(ScrapeLog.created_at.desc())\
                          .paginate(page=page, per_page=20, error_out=False)
    
    # Calculate dataset stats
    stats = db.session.query(ScrapeLog.disease_class, db.func.count(ScrapeLog.id))\
                      .filter(ScrapeLog.status == 'downloaded')\
                      .group_by(ScrapeLog.disease_class).all()
                      
    return render_template('admin/dataset.html', logs=logs, stats=stats)


@admin.route('/model-metrics')
@login_required
@admin_required
def model_metrics():
    """Read latest training metrics from DB or JSON file."""
    import sqlite3
    from datetime import datetime

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    results_json  = os.path.join(BASE_DIR, 'model', 'training_results.json')
    model_h5      = os.path.join(BASE_DIR, 'model', 'millet_disease_model.h5')
    labels_json   = os.path.join(BASE_DIR, 'model', 'class_names.json')
    db_path       = os.path.join(BASE_DIR, 'instance', 'millet.db')

    # ---- gather model file info -------
    model_exists = os.path.exists(model_h5)
    model_size   = None
    if model_exists:
        model_size = round(os.path.getsize(model_h5) / (1024 * 1024), 1)  # MB

    class_names = []
    if os.path.exists(labels_json):
        with open(labels_json) as f:
            class_names = json.load(f)

    # ---- gather metrics (JSON > DB) ---
    metrics_rows = []
    latest       = None

    # Try JSON first
    if os.path.exists(results_json):
        try:
            with open(results_json) as f:
                data = json.load(f)
            latest = data
        except Exception:
            pass

    # Try DB for history
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur  = conn.cursor()
            cur.execute("""
                SELECT id, model_name, training_accuracy, validation_accuracy,
                       loss, validation_loss, trained_at
                FROM model_metrics
                ORDER BY id DESC LIMIT 10
            """)
            metrics_rows = [dict(r) for r in cur.fetchall()]
            conn.close()
            if not latest and metrics_rows:
                row = metrics_rows[0]
                latest = {
                    'model_name':          row.get('model_name', 'N/A'),
                    'training_accuracy':   row.get('training_accuracy'),
                    'validation_accuracy': row.get('validation_accuracy'),
                    'loss':                row.get('loss'),
                    'validation_loss':     row.get('validation_loss'),
                    'trained_at':          row.get('trained_at'),
                }
    except Exception as e:
        print(f'[WARN] model_metrics DB query failed: {e}')

    return render_template('admin/model_metrics.html',
                           model_exists=model_exists,
                           model_size=model_size,
                           class_names=class_names,
                           latest=latest,
                           metrics_rows=metrics_rows)


@admin.route('/api/model-status')
@login_required
@admin_required
def api_model_status():
    """Lightweight JSON endpoint for the dashboard model status widget."""
    import sqlite3
    BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
    results_json = os.path.join(BASE_DIR, 'model', 'training_results.json')
    model_h5     = os.path.join(BASE_DIR, 'model', 'millet_disease_model.h5')
    db_path      = os.path.join(BASE_DIR, 'instance', 'millet.db')

    model_exists = os.path.exists(model_h5)
    data = {'model_exists': model_exists,
            'training_accuracy': None, 'validation_accuracy': None,
            'loss': None, 'validation_loss': None, 'trained_at': None}

    # JSON takes priority
    if os.path.exists(results_json):
        try:
            with open(results_json) as f:
                j = json.load(f)
            data.update({
                'training_accuracy':   j.get('training_accuracy'),
                'validation_accuracy': j.get('validation_accuracy'),
                'loss':                j.get('loss'),
                'validation_loss':     j.get('validation_loss'),
                'trained_at':          j.get('trained_at'),
            })
            return jsonify(data)
        except Exception:
            pass

    # Fallback: DB
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur  = conn.cursor()
            cur.execute("""
                SELECT training_accuracy, validation_accuracy, loss, validation_loss, trained_at
                FROM model_metrics ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
            conn.close()
            if row:
                r = dict(row)
                ta = r.get('training_accuracy')
                va = r.get('validation_accuracy')
                data.update({
                    'training_accuracy':   ta * 100 if ta and ta <= 1.0 else ta,
                    'validation_accuracy': va * 100 if va and va <= 1.0 else va,
                    'loss':                r.get('loss'),
                    'validation_loss':     r.get('validation_loss'),
                    'trained_at':          r.get('trained_at'),
                })
    except Exception as e:
        data['error'] = str(e)

    return jsonify(data)
