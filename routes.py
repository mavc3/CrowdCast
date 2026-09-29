from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from ..models import Service, Stadium, OperationalData, Prediction, PredictionBatch
from .. import db, role_required, log_action
from datetime import datetime, date

staff = Blueprint('staff', __name__)

@staff.route('/dashboard')
@login_required
@role_required(['staff', 'admin'])
def dashboard():
    # Assigned Services Count (Simulated as all for demo, or filter by manager)
    services = Service.query.all()
    active_count = Service.query.filter_by(status='Open').count()
    
    # Today's updates
    today_updates = OperationalData.query.filter(
        db.func.date(OperationalData.timestamp) == date.today()
    ).count()
    
    # Latest Prediction
    latest_pred = Prediction.query.order_by(Prediction.timestamp.desc()).first()
    
    # Generate Critical Alerts (BULK OPTIMIZED)
    alerts = []
    latest_updates = OperationalData.query.order_by(OperationalData.timestamp.desc()).all()
    svc_latest = {}
    for data in latest_updates:
        if data.service_id not in svc_latest:
            svc_latest[data.service_id] = data
            
    for svc in services:
        latest_data = svc_latest.get(svc.id)
        if latest_data and svc.capacity > 0:
            ratio = latest_data.current_capacity / svc.capacity
            if ratio >= 0.85:
                alerts.append({
                    'message': f"CRITICAL: {svc.name} is at {ratio*100:.1f}% capacity. Reallocate resources immediately.",
                    'time': latest_data.timestamp.strftime('%H:%M')
                })
    
    return render_template('staff/dashboard.html', 
                         services=services, 
                         active_count=active_count,
                         today_updates=today_updates,
                         latest_pred=latest_pred,
                         alerts=alerts)

@staff.route('/services')
@login_required
@role_required(['staff', 'admin'])
def services():
    all_services = Service.query.all()
    all_stadiums = Stadium.query.all()
    return render_template('staff/services.html', services=all_services, stadiums=all_stadiums)

@staff.route('/service/add', methods=['POST'])
@login_required
@role_required(['staff', 'admin'])
def add_service():
    name = request.form.get('service_name')
    stadium_id = request.form.get('stadium_id')
    
    # Validation
    existing = Service.query.filter_by(name=name, stadium_id=stadium_id).first()
    if existing:
        flash("Service name already exists in this stadium.", "error")
        return redirect(url_for('staff.services'))
    
    service = Service(
        name=name,
        stadium_id=stadium_id,
        type=request.form.get('category'),
        capacity=request.form.get('capacity'),
        location=request.form.get('location_description'),
        status=request.form.get('status', 'Open')
    )
    db.session.add(service)
    db.session.commit()
    log_action('SERVICE_CREATED', f"Service {service.name} added by {current_user.name}")
    flash(f"Service {name} initialized successfully.", "success")
    return redirect(url_for('staff.services'))

@staff.route('/service/edit/<int:id>', methods=['POST'])
@login_required
@role_required(['staff', 'admin'])
def edit_service(id):
    service = Service.query.get_or_404(id)
    service.capacity = request.form.get('capacity')
    service.status = request.form.get('status')
    service.operating_hours = request.form.get('operating_hours')
    db.session.commit()
    log_action('SERVICE_UPDATED', f"Service {service.name} updated by {current_user.name}")
    flash(f"Service {service.name} updated.", "success")
    return redirect(url_for('staff.services'))

@staff.route('/service/delete/<int:id>', methods=['POST'])
@login_required
@role_required(['staff', 'admin'])
def delete_service(id):
    service = Service.query.get_or_404(id)
    name = service.name
    db.session.delete(service)
    db.session.commit()
    log_action('SERVICE_DELETED', f"Service {name} removed by {current_user.name}")
    flash(f"Service {name} removed from registry.", "info")
    return redirect(url_for('staff.services'))

@staff.route('/data/input', methods=['GET', 'POST'])
@login_required
@role_required(['staff', 'admin'])
def data_input():
    if request.method == 'POST':
        service_id = request.form.get('service_id')
        waiting_time = int(request.form.get('waiting_time', 0))
        current_capacity = int(request.form.get('current_capacity', 0))
        
        # Validation
        service = Service.query.get(service_id)
        if waiting_time < 0 or waiting_time > 300:
            flash("Waiting time must be between 0 and 300 minutes.", "error")
            return redirect(url_for('staff.data_input'))
        
        if current_capacity > service.capacity:
            flash(f"Capacity cannot exceed service maximum ({service.capacity}).", "error")
            return redirect(url_for('staff.data_input'))
            
        data = OperationalData(
            service_id=service_id,
            waiting_time=waiting_time,
            current_capacity=current_capacity,
            availability_status=request.form.get('availability_status'),
            notes=request.form.get('notes')
        )
        db.session.add(data)
        db.session.commit()
        
        # Flagging for feature refresh could be implemented here
        log_action('DATA_INPUT', f"Operational data submitted for {service.name}")
        flash("Telemetry data successfully ingested.", "success")
        return redirect(url_for('staff.data_input'))

    services = Service.query.all()
    return render_template('staff/data_input.html', services=services)

@staff.route('/predictions')
@login_required
@role_required(['staff', 'admin'])
def prediction_viewer():
    stadium_filter = request.args.get('stadium_id')
    service_filter = request.args.get('service_id')
    
    query = Prediction.query.join(Service)
    if stadium_filter:
        query = query.filter(Service.stadium_id == stadium_filter)
    if service_filter:
        query = query.filter(Prediction.service_id == service_filter)
        
    predictions = query.order_by(Prediction.timestamp.desc()).limit(50).all()
    stadiums = Stadium.query.all()
    services = Service.query.all()
    
    return render_template('staff/predictions.html', 
                         predictions=predictions, 
                         stadiums=stadiums, 
                         services=services)
