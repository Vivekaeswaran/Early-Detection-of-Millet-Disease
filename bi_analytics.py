"""
bi_analytics.py – BI Analytics Blueprint for MilletGuard AI
============================================================
All queries are READ-ONLY.  No existing table, model, or route is modified.
"""

import os
import io
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict

from flask import (Blueprint, render_template, jsonify, request,
                   current_app, url_for)

bi_analytics = Blueprint('bi_analytics', __name__, url_prefix='/bi')

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _get_db_path():
    return os.path.join(current_app.instance_path, 'millet.db')


def _query(sql, params=()):
    """Run a read-only SQL query and return list-of-dicts."""
    import sqlite3
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _scalar(sql, params=(), default=0):
    """Run a scalar query and return single value."""
    import sqlite3
    conn = sqlite3.connect(_get_db_path())
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else default
    finally:
        conn.close()


def _date_from_days(days):
    """Return ISO date string N days ago."""
    return (datetime.utcnow() - timedelta(days=int(days))).strftime('%Y-%m-%d')


def _alpha(hex_color, a):
    """Return rgba(r,g,b,a) string from hex color."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f'rgba({r},{g},{b},{a})'

# Alias used in data-building code
ALPHA = _alpha


# ─────────────────────────────────────────────────────────────
# Route 1 – Dashboard Page
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/analytics')
def analytics_page():
    return render_template('bi_analytics.html', active_tab='dashboard')


# ─────────────────────────────────────────────────────────────
# Route 1b – DB Explorer Page (integrated BI tab)
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/db-explorer')
def db_explorer_page():
    return render_template('bi_analytics.html', active_tab='db_explorer')


# ─────────────────────────────────────────────────────────────
# Route 2 – Analytics Data API
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/api/analytics-data')
def analytics_data():
    try:
        # ── Filter params ──────────────────────────────────────────
        days       = request.args.get('days', 30, type=int)
        disease_f  = request.args.get('disease', 'all')
        severity_f = request.args.get('severity', 'all')
        since      = _date_from_days(days)

        base_where = "WHERE sh.scanned_at >= ?"
        base_params = [since]
        if disease_f != 'all':
            base_where += " AND sh.disease_name = ?"
            base_params.append(disease_f)
        if severity_f != 'all':
            base_where += " AND sh.severity = ?"
            base_params.append(severity_f)

        # ── KPI Cards ─────────────────────────────────────────────
        total_scans = _scalar(
            f"SELECT COUNT(*) FROM scan_history sh {base_where}", base_params)

        total_farmers = _scalar(
            "SELECT COUNT(DISTINCT id) FROM users WHERE role='farmer'")

        # Most detected disease (filtered period)
        most_rows = _query(
            f"""SELECT disease_name, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                GROUP BY disease_name ORDER BY cnt DESC LIMIT 1""",
            base_params)
        most_disease = most_rows[0]['disease_name'] if most_rows else 'N/A'

        avg_conf = _scalar(
            f"SELECT AVG(confidence) FROM scan_history sh {base_where}", base_params)
        avg_conf = round(avg_conf or 0, 1)

        healthy_count = _scalar(
            f"""SELECT COUNT(*) FROM scan_history sh {base_where}
                AND sh.disease_name LIKE '%Healthy%'""", base_params)
        healthy_pct = round((healthy_count / total_scans * 100) if total_scans else 0, 1)

        # Active cases = scans with status 'pending' in filtered period
        active_cases = _scalar(
            f"""SELECT COUNT(*) FROM scan_history sh {base_where}
                AND sh.status = 'pending'""", base_params)

        # ── Disease Distribution (Doughnut) ───────────────────────
        disease_dist_rows = _query(
            f"""SELECT disease_name, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                GROUP BY disease_name ORDER BY cnt DESC""",
            base_params)
        disease_dist = {r['disease_name']: r['cnt'] for r in disease_dist_rows}

        # ── Severity Distribution (Polar Area) ────────────────────
        sev_rows = _query(
            f"""SELECT severity, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                AND severity IS NOT NULL
                GROUP BY severity""",
            base_params)
        severity_dist = {r['severity']: r['cnt'] for r in sev_rows}

        # ── Daily Scans Trend (Line) ──────────────────────────────
        daily_rows = _query(
            f"""SELECT DATE(sh.scanned_at) as d, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                GROUP BY d ORDER BY d""",
            base_params)
        daily_labels = [r['d'] for r in daily_rows]
        daily_values = [r['cnt'] for r in daily_rows]

        # ── Disease Trend Over Time (Area) ────────────────────────
        trend_rows = _query(
            f"""SELECT DATE(sh.scanned_at) as d, sh.disease_name, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                GROUP BY d, sh.disease_name ORDER BY d""",
            base_params)

        # Build per-disease time series
        all_dates_set = sorted({r['d'] for r in trend_rows})
        diseases_in_trend = list({r['disease_name'] for r in trend_rows})
        trend_by_disease = defaultdict(lambda: defaultdict(int))
        for r in trend_rows:
            trend_by_disease[r['disease_name']][r['d']] = r['cnt']

        disease_trend_datasets = []
        palette = ['#22c55e','#3b82f6','#ef4444','#f59e0b','#06b6d4',
                   '#a855f7','#f97316','#ec4899','#14b8a6','#6366f1']
        for i, dis in enumerate(diseases_in_trend[:8]):
            color = palette[i % len(palette)]
            disease_trend_datasets.append({
                'label': dis,
                'data': [trend_by_disease[dis].get(d, 0) for d in all_dates_set],
                'borderColor': color,
                'backgroundColor': color + '22',
                'fill': True,
                'tension': 0.4
            })

        # ── Confidence Histogram (Bar) ────────────────────────────
        conf_rows = _query(
            f"""SELECT confidence FROM scan_history sh {base_where}
                AND confidence IS NOT NULL""",
            base_params)
        buckets = [0] * 10  # 0-10, 10-20, ..., 90-100
        for r in conf_rows:
            c = min(float(r['confidence']), 99.99)
            buckets[int(c // 10)] += 1
        conf_labels = ['0-10%','10-20%','20-30%','30-40%','40-50%',
                       '50-60%','60-70%','70-80%','80-90%','90-100%']

        # ── Top Detected Diseases (Horizontal Bar) ────────────────
        top_diseases_rows = _query(
            f"""SELECT disease_name, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                GROUP BY disease_name ORDER BY cnt DESC LIMIT 8""",
            base_params)
        top_dis_labels = [r['disease_name'] for r in top_diseases_rows]
        top_dis_values = [r['cnt'] for r in top_diseases_rows]

        # ── Recovery Progress (Doughnut) ─────────────────────────
        rec_rows = _query(
            """SELECT improvement_status, COUNT(*) as cnt
               FROM redetection_history
               GROUP BY improvement_status""")
        recovery_dist = {r['improvement_status']: r['cnt'] for r in rec_rows}
        # Fallback: if no redetection data, group by recovery_status in treatment_plans
        if not recovery_dist:
            tp_rows = _query(
                """SELECT recovery_status, COUNT(*) as cnt
                   FROM treatment_plans GROUP BY recovery_status""")
            recovery_dist = {r['recovery_status']: r['cnt'] for r in tp_rows}

        # ── Sensor Telemetry (Multi-line) ─────────────────────────
        sensor_rows = _query(
            """SELECT strftime('%Y-%m-%d %H:%M', created_at) as t,
                      temperature, humidity,
                      COALESCE(soil_moisture_percent, soil_moisture) as soil
               FROM sensor_data
               ORDER BY created_at DESC LIMIT 50""")
        sensor_rows = list(reversed(sensor_rows))  # chronological
        sensor_labels = [r['t'] for r in sensor_rows]
        sensor_temp   = [r['temperature'] for r in sensor_rows]
        sensor_hum    = [r['humidity'] for r in sensor_rows]
        sensor_soil   = [r['soil'] for r in sensor_rows]

        # ── Recent Scans Table ────────────────────────────────────
        recent_rows = _query(
            f"""SELECT sh.id, sh.image_path, sh.disease_name,
                       sh.confidence, sh.severity, sh.status,
                       sh.scanned_at, sh.next_follow_up_date
                FROM scan_history sh {base_where}
                ORDER BY sh.scanned_at DESC LIMIT 20""",
            base_params)

        # ── Disease list for filter dropdown ─────────────────────
        all_diseases = _query(
            "SELECT DISTINCT disease_name FROM scan_history WHERE disease_name IS NOT NULL ORDER BY disease_name")
        disease_list = [r['disease_name'] for r in all_diseases]

        # ─────────────── Assemble response (see return below) ────────────────

        # ── Monthly Scan Trend (Grouped Bar) ─────────────────────
        monthly_rows = _query(
            f"""SELECT strftime('%Y-%m', sh.scanned_at) as ym, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                GROUP BY ym ORDER BY ym""",
            base_params)
        monthly_labels = [r['ym'] for r in monthly_rows]
        monthly_values = [r['cnt'] for r in monthly_rows]

        # ── Disease × Severity Breakdown (Stacked Bar) ────────────
        ds_rows = _query(
            f"""SELECT sh.disease_name, sh.severity, COUNT(*) as cnt
                FROM scan_history sh {base_where}
                AND sh.severity IS NOT NULL
                GROUP BY sh.disease_name, sh.severity
                ORDER BY sh.disease_name""",
            base_params)

        # Build structure: {disease: {High:n, Medium:n, Low:n}}
        ds_diseases = list({r['disease_name'] for r in ds_rows})[:10]
        ds_severities = ['High', 'Medium', 'Low']
        ds_map = defaultdict(lambda: defaultdict(int))
        for r in ds_rows:
            ds_map[r['disease_name']][r['severity']] = r['cnt']
        ds_datasets = []
        sev_palette = {'High': '#ef4444', 'Medium': '#f59e0b', 'Low': '#22c55e'}
        for sev in ds_severities:
            ds_datasets.append({
                'label': sev,
                'data': [ds_map[d].get(sev, 0) for d in ds_diseases],
                'backgroundColor': ALPHA(sev_palette[sev], 0.75),
                'borderColor': sev_palette[sev],
                'borderWidth': 1,
                'borderRadius': 4,
            })

        return jsonify({
            'kpis': {
                'total_scans':   total_scans,
                'total_farmers': total_farmers,
                'most_disease':  most_disease,
                'avg_confidence': avg_conf,
                'healthy_pct':   healthy_pct,
                'active_cases':  active_cases,
            },
            'disease_dist':     disease_dist,
            'severity_dist':    severity_dist,
            'daily_labels':     daily_labels,
            'daily_values':     daily_values,
            'trend_labels':     list(all_dates_set),
            'trend_datasets':   disease_trend_datasets,
            'conf_labels':      conf_labels,
            'conf_values':      buckets,
            'top_dis_labels':   top_dis_labels,
            'top_dis_values':   top_dis_values,
            'recovery_dist':    recovery_dist,
            'sensor_labels':    sensor_labels,
            'sensor_temp':      sensor_temp,
            'sensor_hum':       sensor_hum,
            'sensor_soil':      sensor_soil,
            'recent_scans':     recent_rows,
            'disease_list':     disease_list,
            'monthly_labels':   monthly_labels,
            'monthly_values':   monthly_values,
            'ds_labels':        ds_diseases,
            'ds_datasets':      ds_datasets,
        })

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(exc)}), 500



# ─────────────────────────────────────────────────────────────
# Route 3 – Dataset Upload & Route 6 – Chart Builder
# (Both defined below after the DB Explorer routes, with in-memory cache)
# ─────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────
# Route 4 – DB Explorer: List Tables
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/api/db-tables')
def api_db_tables():
    """Return list of all user tables in the SQLite database."""
    try:
        rows = _query(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")
        return jsonify({'tables': [r['name'] for r in rows]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# Route 5 – DB Explorer: Paginated Table Data
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/api/db-table-data')
def api_db_table_data():
    """Return paginated, searchable rows from a specific table."""
    import sqlite3
    try:
        table    = request.args.get('table', '').strip()
        page     = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        search   = request.args.get('search', '').strip()

        if not table:
            return jsonify({'error': 'table parameter required'}), 400

        # Whitelist: only allow real SQLite user tables (prevents injection)
        valid_tables = [r['name'] for r in _query(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%'")]
        if table not in valid_tables:
            return jsonify({'error': 'Invalid table name'}), 400

        # Get columns via PRAGMA
        col_rows = _query(f"PRAGMA table_info({table})")
        columns  = [c['name'] for c in col_rows]

        # Build count + data query
        offset      = (page - 1) * per_page
        base_sql    = f'SELECT * FROM "{table}"'
        count_sql   = f'SELECT COUNT(*) FROM "{table}"'
        params      = []

        if search and columns:
            clauses   = ' OR '.join([f'"{c}" LIKE ?' for c in columns])
            where     = f' WHERE {clauses}'
            search_p  = [f'%{search}%'] * len(columns)
            base_sql += where
            count_sql += where
            params    = search_p

        conn = sqlite3.connect(_get_db_path())
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute(count_sql, params)
            total_rows = cur.fetchone()[0]

            cur.execute(base_sql + ' LIMIT ? OFFSET ?', params + [per_page, offset])
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

        total_pages = max(1, (total_rows + per_page - 1) // per_page)
        return jsonify({
            'table':       table,
            'columns':     columns,
            'rows':        rows,
            'total_rows':  total_rows,
            'total_pages': total_pages,
            'page':        page,
            'per_page':    per_page,
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# Route 6 – Custom Chart Builder (from uploaded dataset in session)
# ─────────────────────────────────────────────────────────────

# In-process cache: stores last uploaded DataFrame per Flask worker.
# Cleared on new upload. Thread-safe via read-only access after write.
_BI_DATASET_CACHE = {}

@bi_analytics.route('/api/upload-dataset', methods=['POST'])
def upload_dataset():
    """
    Accept CSV/Excel upload, cache the DataFrame in-process, return preview + auto-charts.
    ALWAYS returns HTTP 200 — errors are in the JSON 'error' key, never as HTTP 4xx/5xx.
    """
    # ── pandas check ───────────────────────────────────────────────────────
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'error': 'pandas is not installed — run: pip install pandas openpyxl'})

    # ── Get file ───────────────────────────────────────────────────────────
    f = request.files.get('file')
    if f is None or (f.filename or '') == '':
        return jsonify({'error': 'No file uploaded. Please choose a CSV or Excel file.'})

    filename = f.filename.strip().lower()
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        return jsonify({'error': 'Only CSV (.csv) or Excel (.xlsx / .xls) files are allowed.'})

    # ── Parse ──────────────────────────────────────────────────────────────
    try:
        raw = f.read()   # read once into memory

        if filename.endswith('.csv'):
            # Try encodings in order: utf-8 → latin-1 → cp1252
            df = None
            for enc in ('utf-8', 'latin-1', 'cp1252'):
                try:
                    df = pd.read_csv(io.BytesIO(raw), encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            if df is None:
                # Last resort: ignore bad bytes
                df = pd.read_csv(io.BytesIO(raw), encoding='utf-8', errors='ignore')
        else:
            # Excel: openpyxl for .xlsx, xlrd for .xls
            engine = 'openpyxl' if filename.endswith('.xlsx') else None
            df = pd.read_excel(io.BytesIO(raw), engine=engine)

    except Exception as e:
        return jsonify({'error': 'File parsing failed', 'details': str(e)})

    # ── Clean up ───────────────────────────────────────────────────────────
    try:
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        # Drop columns that are 100% empty
        df = df.dropna(axis=1, how='all')
        # Drop rows that are 100% empty
        df = df.dropna(axis=0, how='all').reset_index(drop=True)
    except Exception:
        pass   # never let cleanup crash the whole route

    # ── Cache for chart builder ────────────────────────────────────────────
    _BI_DATASET_CACHE['df']       = df
    _BI_DATASET_CACHE['filename'] = f.filename

    total_rows = len(df)
    columns    = list(df.columns)

    # ── Preview (20 rows, JSON-safe) ───────────────────────────────────────
    try:
        # Slice FIRST, then fillna — avoids shape-mismatch bug in older pandas
        preview_df   = df.head(20).copy()
        preview_data = preview_df.fillna('').astype(str).to_dict(orient='records')
    except Exception:
        preview_data = []

    # ── Auto-charts: numeric columns (up to 4) ────────────────────────────
    numeric_charts = []
    try:
        for col in df.select_dtypes(include='number').columns[:4]:
            vals = df[col].dropna().head(50)
            # Cast to plain Python float so jsonify never chokes on numpy types
            numeric_charts.append({
                'label':  col,
                'values': [float(v) for v in vals],
            })
    except Exception:
        pass

    # ── Auto-charts: categorical columns (up to 3) ────────────────────────
    category_charts = []
    try:
        for col in df.select_dtypes(include='object').columns[:3]:
            counts = df[col].value_counts().head(10)
            category_charts.append({
                'label':  col,
                'labels': [str(x) for x in counts.index.tolist()],
                'values': [int(v) for v in counts.values.tolist()],
            })
    except Exception:
        pass

    return jsonify({
        'status':          'success',
        'columns':         columns,
        'rows':            total_rows,      # spec key
        'total_rows':      total_rows,      # legacy key kept for existing JS
        'preview':         preview_data,    # list of dicts, fully JSON-safe
        'numeric_charts':  numeric_charts,
        'category_charts': category_charts,
    })


@bi_analytics.route('/api/build-chart', methods=['POST'])
def build_chart():
    """
    Build a custom chart from the cached uploaded dataset.
    Payload (JSON): { x_col, y_col, chart_type }
    chart_type: bar | line | pie | scatter
    """
    try:
        import pandas as pd
    except ImportError:
        return jsonify({'error': 'pandas not installed'})

    df = _BI_DATASET_CACHE.get('df')
    if df is None:
        return jsonify({'error': 'No dataset uploaded yet. Please upload a CSV or Excel file first.'})

    data = request.get_json(silent=True) or {}
    x_col      = data.get('x_col', '')
    y_col      = data.get('y_col', '')
    chart_type = data.get('chart_type', 'bar')

    if x_col not in df.columns:
        return jsonify({'error': f'Column "{x_col}" not found in dataset.'})

    palette = ['#22c55e','#3b82f6','#ef4444','#f59e0b','#06b6d4',
               '#a855f7','#f97316','#ec4899','#14b8a6','#6366f1']

    try:
        if chart_type == 'scatter':
            # Scatter: both axes must be numeric
            if y_col not in df.columns:
                return jsonify({'error': f'Column "{y_col}" not found.'}), 400
            sub = df[[x_col, y_col]].dropna().head(200)
            points = [{'x': float(row[x_col]), 'y': float(row[y_col])} for _, row in sub.iterrows()]
            chart_data = {
                'type': 'scatter',
                'data': {
                    'datasets': [{
                        'label': f'{x_col} vs {y_col}',
                        'data': points,
                        'backgroundColor': palette[0] + 'aa',
                        'pointRadius': 4,
                    }]
                }
            }

        elif chart_type == 'pie':
            # Pie: x is category, y is value (or count if y is absent/same as x)
            if y_col and y_col in df.columns and y_col != x_col:
                agg = df.groupby(x_col)[y_col].sum().head(12)
            else:
                agg = df[x_col].value_counts().head(12)
            labels = [str(l) for l in agg.index.tolist()]
            values = [float(v) for v in agg.values.tolist()]
            chart_data = {
                'type': 'pie',
                'data': {
                    'labels': labels,
                    'datasets': [{
                        'data': values,
                        'backgroundColor': palette[:len(labels)],
                        'borderWidth': 2,
                        'borderColor': '#111827',
                    }]
                }
            }

        else:
            # Bar or Line
            if y_col and y_col in df.columns and y_col != x_col:
                agg = df.groupby(x_col)[y_col].sum().head(20)
                labels = [str(l) for l in agg.index.tolist()]
                values = [float(v) for v in agg.values.tolist()]
                y_label = y_col
            else:
                cnt = df[x_col].value_counts().head(20)
                labels = [str(l) for l in cnt.index.tolist()]
                values = [float(v) for v in cnt.values.tolist()]
                y_label = 'Count'

            chart_data = {
                'type': chart_type,
                'data': {
                    'labels': labels,
                    'datasets': [{
                        'label': y_label,
                        'data': values,
                        'backgroundColor': [c + 'cc' for c in palette[:len(labels)]],
                        'borderColor': palette[0],
                        'borderWidth': 2,
                        'borderRadius': 6 if chart_type == 'bar' else 0,
                        'tension': 0.4,
                        'fill': chart_type == 'line',
                    }]
                }
            }

        return jsonify({'chart': chart_data, 'x_col': x_col, 'y_col': y_col})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────
# Route 7 – Model Metrics (public read-only, for BI tab)
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/api/model-metrics')
def api_model_metrics():
    """Return latest model training metrics for BI Analytics display."""
    import sqlite3
    BASE_DIR     = os.path.join(current_app.root_path)
    results_json = os.path.join(BASE_DIR, 'model', 'training_results.json')
    model_h5     = os.path.join(BASE_DIR, 'model', 'millet_disease_model.h5')
    db_path      = os.path.join(current_app.instance_path, 'millet.db')

    result = {'model_exists': os.path.exists(model_h5)}

    if os.path.exists(results_json):
        try:
            with open(results_json) as f:
                result.update(json.load(f))
            return jsonify(result)
        except Exception:
            pass

    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur  = conn.cursor()
            cur.execute("""
                SELECT model_name, training_accuracy, validation_accuracy,
                       loss, validation_loss, trained_at
                FROM model_metrics ORDER BY id DESC LIMIT 1
            """)
            row = cur.fetchone()
            conn.close()
            if row:
                result.update(dict(row))
    except Exception as e:
        result['error'] = str(e)

    return jsonify(result)


# ─────────────────────────────────────────────────────────────
# Route Aliases (required by spec, delegate to existing handlers)
# ─────────────────────────────────────────────────────────────

@bi_analytics.route('/api/generate-dataset-chart', methods=['POST'])
def generate_dataset_chart():
    """
    Alias for /bi/api/build-chart.
    Spec requires this route name; logic is identical.
    """
    return build_chart()
