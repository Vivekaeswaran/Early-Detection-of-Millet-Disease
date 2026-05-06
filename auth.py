from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User

auth = Blueprint('auth', __name__)

@auth.route('/login/farmer', methods=['GET', 'POST'])
def farmer_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email, role='farmer').first()
        if user and check_password_hash(user.password, password):
            if user.is_blocked:
                flash('Your account has been blocked. Contact admin.', 'danger')
                return redirect(url_for('auth.farmer_login'))
            login_user(user)
            return redirect(url_for('farmer.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('farmer/login.html')

@auth.route('/register/farmer', methods=['GET', 'POST'])
def farmer_register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        location = request.form.get('location', '').strip()
        crop_type = request.form.get('crop_type', '').strip()
        phone = request.form.get('phone', '').strip()

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return redirect(url_for('auth.farmer_register'))

        user = User(name=name, email=email,
                    username=email.split('@')[0], # Default username from email
                    password=generate_password_hash(password),
                    role='farmer', location=location,
                    crop_type=crop_type, phone=phone,
                    status='Active') # Set default status
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('auth.farmer_login'))
    return render_template('farmer/register.html')

@auth.route('/login/expert', methods=['GET', 'POST'])
def expert_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email, role='expert').first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('expert.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('expert/login.html')

@auth.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email, role='admin').first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('admin/login.html')

@auth.route('/logout')
@login_required
def logout():
    role = current_user.role
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))
