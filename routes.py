import csv
import io
import os
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from ..models import User, Stadium, Service, Prediction, PredictionBatch, SystemLog
from ..prediction_engine import PredictionEngine
from .. import db, role_required, log_action

admin = Blueprint('admin', __name__)
engine = PredictionEngine()

@admin.route('/dashboard')
@login_required
@role_required(['admin'])
def dashboard():
    from sqlalchemy import func
    from app.models import User, Stadium, Service, Prediction, PredictionBatch, Visit, SystemLog
    from datetime import datetime, timedelta
    
    # KPIs
    stats = {
        'users': f"{User.query.filter(User.role != 'visitor').count():,}",
        'visitors': f"{User.query.filter(User.role == 'visitor').count():,}",
        'services': f"{Service.query.count():,}",
        'stadiums': f"{Stadium.query.count():,}",
        'predictions': f"{Prediction.query.count():,}"
    }
    
    # Velocity Trend (Extract hour from timestamp)
    velocity_query = db.session.query(
        func.extract('hour', Prediction.timestamp), 
        func.avg(Prediction.expected_visitors)
    ).group_by(func.extract('hour', Prediction.timestamp)).all()
    
    # Create a dense 24-hour map to avoid chart gaps
    v_map = {int(h): 0 for h in range(24)}
    for v in velocity_query:
        if v[0] is not None: v_map[int(v[0])] = int(v[1])
        
    v_labels = [f"{h:02d}:00" for h in range(24)]
    v_values = [v_map[h] for h in range(24)]

    # Demand Pie - Standardized Mapping
    demand_query = db.session.query(
        Prediction.demand_level, 
        func.count(Prediction.id)
    ).group_by(Prediction.demand_level).all()

    labels = ['Low', 'Medium', 'High', 'Critical']
    d_map = {l: 0 for l in labels}
    
    # Map both numeric strings and descriptive strings
    idx_map = {'0': 'Low', '1': 'Medium', '2': 'High', '3': 'Critical'}
    
    for row in demand_query:
        key = str(row[0])
        mapped_key = idx_map.get(key, key)
        if mapped_key in d_map:
            d_map[mapped_key] += int(row[1])
        else:
            d_map['Medium'] += int(row[1]) # Default fallback

    chart_data = {
        'velocity_labels': v_labels,
        'velocity_values': v_values,
        'demand_labels': labels,
        'demand_values': [d_map[l] for l in labels]
    }
    
    # 1. Heatmap: All services occupancy (BULK QUERY)
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # Single query to get all counts grouped by service_id
    visit_counts_query = db.session.query(
        Visit.service_id, 
        func.count(Visit.id)
    ).filter(Visit.timestamp >= one_hour_ago).group_by(Visit.service_id).all()
    
    visit_counts = {vc[0]: vc[1] for vc in visit_counts_query}
    
    services = Service.query.all()
    heatmap_data = []
    
    for svc in services:
        active_count = visit_counts.get(svc.id, 0)
        occ = round(min(1.0, active_count / svc.capacity) * 100, 1) if svc.capacity > 0 else 0
        heatmap_data.append({'id': svc.id, 'name': svc.name, 'val': occ})
        
    # 2. Zones: Group by Stadium (BULK QUERY)
    stadiums = Stadium.query.all()
    zone_data = []
    
    # Single query to get stadium-level visitor counts
    stadium_counts_query = db.session.query(
        Service.stadium_id,
        func.count(Visit.id)
    ).join(Visit, Visit.service_id == Service.id)\
     .filter(Visit.timestamp >= one_hour_ago)\
     .group_by(Service.stadium_id).all()
    
    st_counts = {sc[0]: sc[1] for sc in stadium_counts_query}
    
    for st in stadiums:
        st_active = st_counts.get(st.id, 0)
        st_cap = sum([s.capacity for s in st.services])
        pressure = round(st_active / st_cap * 5, 1) if st_cap > 0 else 0
        zone_data.append({
            'name': st.name, 
            'val': pressure, 
            'pct': round(min(1.0, st_active / st_cap) * 100, 1) if st_cap > 0 else 0
        })

    service_counts_query = db.session.query(
        Visit.service_id, 
        func.count(Visit.id)
    ).filter(Visit.timestamp >= one_hour_ago).group_by(Visit.service_id).all()
    
    svc_counts = {sc[0]: sc[1] for sc in service_counts_query}
    
    for svc in services:
        svc_active = svc_counts.get(svc.id, 0)
        pressure = round(svc_active / svc.capacity * 5, 1) if svc.capacity > 0 else 0
        zone_data.append({
            'name': f"{svc.name} ({svc.stadium.name})", 
            'val': pressure,
            'pct': round(min(1.0, svc_active / svc.capacity) * 100, 1) if svc.capacity > 0 else 0
        })
        
    zone_data = sorted(zone_data, key=lambda x: x['val'], reverse=True)

    autopilot_logs = PredictionBatch.query.filter_by(status='Completed').order_by(PredictionBatch.timestamp.desc()).limit(5).all()
    activities = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(10).all()
    
    # Latest Predictions for table
    latest_preds = Prediction.query.order_by(Prediction.timestamp.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html', 
                          stats=stats, 
                          activities=activities, 
                          chart_data=chart_data, 
                          autopilot_logs=autopilot_logs,
                          heatmap_data=heatmap_data,
                          zone_data=zone_data,
                          latest_preds=latest_preds)

@admin.route('/users')
@login_required
@role_required(['admin'])
def user_management():
    page = request.args.get('page', 1, type=int)
    users_pagination = User.query.paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', users=users_pagination)

@admin.route('/stadiums-services', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def stadiums_services():
    if request.method == 'POST':
        # Logic is handled by separate direct endpoints to maintain form clarity
        pass
    stadiums = Stadium.query.all()
    services = Service.query.all()
    return render_template('admin/stadiums_services.html', stadiums=stadiums, services=services)

@admin.route('/prediction-management')
@login_required
@role_required(['admin'])
def prediction_hub():
    from sqlalchemy.orm import joinedload
    
    # Dual Pagination
    batch_page = request.args.get('batch_page', 1, type=int)
    result_page = request.args.get('result_page', 1, type=int)
    
    # Eager Loading to kill N+1 queries
    batches_pagination = PredictionBatch.query.order_by(PredictionBatch.timestamp.desc())\
                        .paginate(page=batch_page, per_page=10, error_out=False)
                        
    results_pagination = Prediction.query.options(joinedload(Prediction.service).joinedload(Service.stadium))\
                        .order_by(Prediction.timestamp.desc())\
                        .paginate(page=result_page, per_page=50, error_out=False)
                        
    return render_template('admin/prediction_hub.html', 
                         batches=batches_pagination, 
                         results=results_pagination)

@admin.route('/reports-page')
@login_required
@role_required(['admin'])
def reports_page():
    from sqlalchemy import func
    
    # Demand Distribution
    demand_stats = db.session.query(
        Prediction.demand_level, 
        func.count(Prediction.id)
    ).group_by(Prediction.demand_level).all()
    
    # Stadium Utilization (Grouped visitors by stadium)
    stadium_stats = db.session.query(
        Stadium.name,
        func.sum(Prediction.expected_visitors)
    ).join(Service, Service.stadium_id == Stadium.id)\
     .join(Prediction, Prediction.service_id == Service.id)\
     .group_by(Stadium.name).all()

    # Performance KPI
    total_visitors = db.session.query(func.sum(Prediction.expected_visitors)).scalar() or 0
    total_preds = Prediction.query.count()
    
    # Prepare data for JS
    reports = {
        'demand_labels': [s[0] for s in demand_stats],
        'demand_values': [s[1] for s in demand_stats],
        'stadium_labels': [s[0] for s in stadium_stats],
        'stadium_values': [int(s[1]) if s[1] else 0 for s in stadium_stats],
        'total_visitors': f"{total_visitors:,}",
        'total_count': f"{total_preds:,}"
    }
    
    return render_template('admin/reports.html', data=reports)

@admin.route('/notifications')
@login_required
@role_required(['admin'])
def notifications():
    return render_template('admin/notifications.html')

@admin.route('/logs')
@login_required
@role_required(['admin'])
def system_logs():
    page = request.args.get('page', 1, type=int)
    logs_pagination = SystemLog.query.order_by(SystemLog.timestamp.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/logs.html', logs=logs_pagination)

@admin.route('/users/add', methods=['POST'])
@login_required
@role_required(['admin'])
def add_user():
    user = User(name=request.form.get('name'), email=request.form.get('email'), password=generate_password_hash(request.form.get('password'), method='pbkdf2:sha256'), role=request.form.get('role'))
    db.session.add(user)
    db.session.commit()
    log_action('USER_CREATED', f"User {user.email} created as {user.role}")
    return redirect(url_for('admin.user_management'))

@admin.route('/prediction/upload', methods=['POST'])
@login_required
@role_required(['admin'])
def upload_dataset():
    file = request.files.get('dataset')
    if not file or not file.filename.endswith('.csv'):
        flash('Invalid CSV File')
        return redirect(url_for('admin.dataset_upload_page'))
    
    batch = PredictionBatch(user_id=current_user.id, status='Processing')
    db.session.add(batch)
    db.session.commit()
    
    upload_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'uploads', f"{batch.id}.csv")
    file.save(upload_path)
    
    # Automated Execution Trigger
    try:
        import pandas as pd
        df = pd.read_csv(upload_path)
        count = 0
        for _, row in df.iterrows():
            feature_data = {
                'stadium_id': row.get('stadium_id', 0),
                'service_id': row.get('service_id', 0),
                'hour': row.get('hour', 12),
                'day_of_week': row.get('day_of_week', 0),
                'service_capacity': row.get('service_capacity', 100)
            }
            visitors, level = engine.predict(feature_data)
            pred = Prediction(
                batch_id=batch.id,
                service_id=int(row.get('service_id')),
                expected_visitors=visitors,
                demand_level=level,
                waiting_time=int(row.get('waiting_time', 15))
            )
            db.session.add(pred)
            count += 1
            
        batch.status = 'Completed'
        batch.records_count = count
        db.session.commit()
        log_action('AUTO_INFERENCE_COMPLETE', f"Batch {batch.id} executed automatically ({count} rows)")
        flash(f"Batch #{batch.id} processed automatically. Results ready in matrix.")
        return redirect(url_for('admin.prediction_results'))
    except Exception as e:
        db.session.rollback()
        batch.status = 'Failed'
        db.session.commit()
        log_action('AUTO_INFERENCE_FAILED', str(e))
        flash(f"Automated processing failed: {str(e)}")
        return redirect(url_for('admin.prediction_control'))

@admin.route('/prediction/execute/<int:batch_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def execute_prediction(batch_id):
    # This route remains for manual retry if needed, but primary flow is automated
    if not engine.is_ready():
        return {"error": "ML Models not loaded"}, 500
        
    batch = PredictionBatch.query.get_or_404(batch_id)
    upload_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'uploads', f"{batch.id}.csv")
    
    try:
        import pandas as pd
        df = pd.read_csv(upload_path)
        Prediction.query.filter_by(batch_id=batch_id).delete()
        
        count = 0
        for _, row in df.iterrows():
            feature_data = {'stadium_id': row.get('stadium_id', 0), 'service_id': row.get('service_id', 0), 
                            'hour': row.get('hour', 12), 'day_of_week': row.get('day_of_week', 0), 
                            'service_capacity': row.get('service_capacity', 100)}
            visitors, level = engine.predict(feature_data)
            pred = Prediction(batch_id=batch.id, service_id=int(row.get('service_id')), 
                              expected_visitors=visitors, demand_level=level, waiting_time=int(row.get('waiting_time', 15)))
            db.session.add(pred)
            count += 1
            
        batch.status = 'Completed'
        batch.records_count = count
        db.session.commit()
        return {"success": True, "batch_id": batch.id, "records": count}
    except Exception as e:
        db.session.rollback()
        return {"error": str(e)}, 500
