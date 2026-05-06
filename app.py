import os
import json
from flask import Flask, render_template, redirect, url_for, session, request, jsonify, Blueprint
from flask_login import LoginManager
from models import db, User, ScanHistory, SensorData

# Load translations globally to save memory
TRANSLATIONS = {}
def load_translations():
    global TRANSLATIONS
    base_dir = os.path.abspath(os.path.dirname(__file__))
    trans_dir = os.path.join(base_dir, 'translations')
    if os.path.exists(trans_dir):
        for lang in ['en', 'ta']:
            path = os.path.join(trans_dir, f'{lang}.json')
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    TRANSLATIONS[lang] = json.load(f)
            else:
                TRANSLATIONS[lang] = {}

load_translations()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'millet-disease-detection-secret-key-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///millet.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'index'
    login_manager.login_message = 'Please login to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from auth import auth
    from farmer import farmer
    from expert import expert
    from admin import admin as admin_bp

    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(farmer)
    app.register_blueprint(expert)
    app.register_blueprint(admin_bp)

    # BI Analytics — read-only, no impact on existing blueprints
    from bi_analytics import bi_analytics
    app.register_blueprint(bi_analytics)

    @app.before_request
    def set_default_language():
        if 'lang' not in session:
            session['lang'] = 'en'

    @app.context_processor
    def inject_translation():
        def t(key, default=None):
            lang = session.get('lang', 'en')
            # Fallback to English if translation is missing in Tamil
            val = TRANSLATIONS.get(lang, {}).get(key)
            if not val and lang != 'en':
                val = TRANSLATIONS.get('en', {}).get(key)
            return val if val else (default if default else key)
        return dict(t=t, current_lang=session.get('lang', 'en'))

    @app.route('/set_language/<lang>')
    def set_language(lang):
        if lang in ['en', 'ta']:
            session['lang'] = lang
        next_url = request.args.get('next') or request.referrer or url_for('index')
        return redirect(next_url)

    @app.route('/')
    def index():
        return render_template('welcome.html')

    @app.route('/select-login')
    def select_login():
        return render_template('login_select.html')


    @app.route('/view-database')
    def view_database():
        import sqlite3
        from flask import request
        db_path = os.path.join(app.instance_path, 'millet.db')
        
        # Mapping for display names to actual table names
        table_mapping = {
            'users': 'users',
            'history': 'scan_history',
            'expert_advice': 'expert_advice',
            'reports': 'reports',
            'sensor_data': 'sensor_data',
            'scrape_logs': 'scrape_logs',
            'notifications': 'notifications',
            'model_metrics': 'model_metrics'
        }
        
        display_tables = list(table_mapping.keys())
        selected_display = request.args.get('table', 'users')
        if selected_display not in display_tables:
            selected_display = 'users'
            
        selected_table = table_mapping.get(selected_display, 'users')
        page = request.args.get('page', 1, type=int)
        per_page = 50
        offset = (page - 1) * per_page
        search = request.args.get('search', '')
        
        columns = []
        rows = []
        total_rows = 0
        error = None
        total_pages = 1
        
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query based on search
            query = f"SELECT * FROM {selected_table}"
            count_query = f"SELECT COUNT(*) FROM {selected_table}"
            params = []
            
            # Fetch columns for search and display
            cursor.execute(f"PRAGMA table_info({selected_table})")
            columns_info = cursor.fetchall()
            if columns_info:
                columns = [col['name'] for col in columns_info]
            
                if search:
                    search_clauses = [f"{col} LIKE ?" for col in columns]
                    where_clause = " WHERE " + " OR ".join(search_clauses)
                    query += where_clause
                    count_query += where_clause
                    params = [f"%{search}%" for _ in columns]
            
            # Get total rows for pagination
            cursor.execute(count_query, params)
            total_rows = cursor.fetchone()[0]
            total_pages = max(1, (total_rows + per_page - 1) // per_page)
            
            # Get paginated data
            query += " LIMIT ? OFFSET ?"
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            # If PRAGMA didn't work, fetch from description
            if not columns and cursor.description:
                columns = [desc[0] for desc in cursor.description]
                
            rows = [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            error = str(e)
            import traceback
            print(traceback.format_exc())
        finally:
            if 'conn' in locals():
                conn.close()
                
        return render_template('view_database.html', 
                               tables=display_tables, 
                               selected_table=selected_display,
                               columns=columns, 
                               rows=rows, 
                               page=page, 
                               total_pages=total_pages,
                               total_rows=total_rows,
                               search=search,
                               error=error)

    @app.route('/api/sensor-data', methods=['POST'])
    def sensor_data_api():
        try:
            from datetime import datetime, timezone, timedelta
            _IST = timezone(timedelta(hours=5, minutes=30))

            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            print("Received sensor JSON:", data)

            humidity             = data.get('humidity')
            temperature          = data.get('temperature')
            soil_moisture_raw    = data.get('soil_moisture_raw')
            soil_moisture_percent = data.get('soil_moisture_percent')
            soil_moisture        = data.get('soil_moisture', soil_moisture_percent)
            status               = data.get('status', 'Unknown')

            if humidity is None or (soil_moisture is None and soil_moisture_percent is None):
                return jsonify({"error": "Missing sensor fields"}), 400

            # Stamp IST time explicitly at insertion
            now_ist = datetime.now(_IST).replace(tzinfo=None)

            new_data = SensorData(
                humidity             = float(humidity),
                temperature          = float(temperature) if temperature is not None else 0.0,
                soil_moisture        = float(soil_moisture_percent) if soil_moisture_percent is not None else float(soil_moisture),
                soil_moisture_raw    = int(soil_moisture_raw) if soil_moisture_raw is not None else None,
                soil_moisture_percent= float(soil_moisture_percent) if soil_moisture_percent is not None else None,
                status               = status,
                created_at           = now_ist,    # ← correct IST timestamp
            )
            db.session.add(new_data)
            db.session.commit()

            return jsonify({
                "message":    "Data saved successfully",
                "id":         new_data.id,
                "created_at": now_ist.strftime('%H:%M:%S | %d %b %Y (IST)')
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sensor-data/latest', methods=['GET'])
    def get_latest_sensor_data():
        try:
            latest = SensorData.query.order_by(SensorData.created_at.desc()).first()
            if not latest:
                return jsonify({"error": "No sensor data found"}), 404

            return jsonify({
                "humidity":             latest.humidity,
                "temperature":          latest.temperature,
                "soil_moisture":        latest.soil_moisture,
                "soil_moisture_raw":    latest.soil_moisture_raw,
                "soil_moisture_percent":latest.soil_moisture_percent,
                "status":               latest.status,
                # stored as IST — format and label it
                "created_at": latest.created_at.strftime('%H:%M:%S | %d %b %Y') + ' IST',
                "created_at_iso": latest.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/sensor-data/history', methods=['GET'])
    def get_sensor_history():
        """Return the last 20 sensor readings for the live history table."""
        try:
            limit = request.args.get('limit', 20, type=int)
            rows = SensorData.query.order_by(SensorData.created_at.desc()).limit(limit).all()
            return jsonify([{
                "id":           r.id,
                "temperature":  r.temperature,
                "humidity":     r.humidity,
                "soil_moisture": r.soil_moisture,
                "status":       r.status,
                "created_at":   r.created_at.strftime('%H:%M:%S | %d %b %Y') + ' IST',
            } for r in rows]), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.errorhandler(404)
    def not_found(e):
        return render_template('404.html'), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template('welcome.html'), 413

    with app.app_context():
        db.create_all()
        # Create uploads and reports directories
        os.makedirs(os.path.join(app.root_path, 'static', 'uploads'), exist_ok=True)
        os.makedirs(os.path.join(app.root_path, 'static', 'reports'), exist_ok=True)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
