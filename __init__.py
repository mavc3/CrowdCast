from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_socketio import SocketIO
from functools import wraps
from flask import abort
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO(cors_allowed_origins="*")

@socketio.on('connect', namespace='/admin')
def admin_connect():
    print("S.IO: ADMIN_COMM_ESTABLISHED")

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_action(action_type, details=None):
    from .models import SystemLog
    new_log = SystemLog(user_id=current_user.id if current_user.is_authenticated else None, action_type=action_type, details=details)
    db.session.add(new_log)
    db.session.commit()

def start_autopilot(app):
    import time
    import random
    from .models import Service, Prediction, PredictionBatch, User, Visit, Stadium
    from .prediction_engine import PredictionEngine

    def run_simulation():
        # Delay start to ensure server is ready
        time.sleep(5)
        engine = PredictionEngine()
        
        while True:
            try:
                with app.app_context():
                    services = Service.query.all()
                    if services and engine.is_ready():
                        batch = PredictionBatch(status='Autopilot', user_id=None)
                        db.session.add(batch)
                        db.session.commit()
                        
                        # Stimulate Check-ins
                        visitors = User.query.filter_by(role='visitor').all()
                        sample = random.sample(services, min(len(services), 8))
                        
                        for s in sample:
                            if random.random() < 0.5:
                                v_count = random.randint(5, 20)
                                for _ in range(v_count):
                                    new_v = Visit(user_id=random.choice(visitors).id, service_id=s.id)
                                    db.session.add(new_v)
                        db.session.commit()

                        # Inference Core
                        pred_data = []
                        for s in sample:
                            st = Stadium.query.get(s.stadium_id)
                            if not st: continue
                            
                            v_count, level = engine.predict(s, st)
                            pred = Prediction(batch_id=batch.id, service_id=s.id, expected_visitors=v_count, demand_level=level)
                            db.session.add(pred)
                            pred_data.append({'service_name': s.name, 'stadium_name': st.name, 'visitors': v_count, 'level': level, 'time': time.strftime('%H:%M:%S')})
                        
                        batch.status = 'Completed'
                        batch.records_count = len(sample)
                        db.session.commit()

                        # Strategic Telemetry Expansion 
                        from datetime import datetime, timedelta
                        now = datetime.utcnow()
                        one_hour_ago = now - timedelta(hours=1)
                        
                        stadiums = Stadium.query.all()
                        z_tele = []
                        for stm in stadiums:
                            stm_svcs = [svc.id for svc in stm.services]
                            stm_active = Visit.query.filter(Visit.service_id.in_(stm_svcs), Visit.timestamp >= one_hour_ago).count()
                            stm_cap = sum([svc.capacity for svc in stm.services])
                            pressure = round(stm_active / stm_cap * 5, 1) if stm_cap > 0 else 0
                            z_tele.append({'name': stm.name, 'val': pressure})

                        services = Service.query.all()
                        for svc in services:
                            svc_active = Visit.query.filter(Visit.service_id == svc.id, Visit.timestamp >= one_hour_ago).count()
                            pressure = round(svc_active / svc.capacity * 5, 1) if svc.capacity > 0 else 0
                            z_tele.append({'name': f"{svc.name} ({svc.stadium.name})", 'val': pressure})
                        
                        z_tele = sorted(z_tele, key=lambda x: x['val'], reverse=True)

                        from sqlalchemy import func
                        d_query = db.session.query(Prediction.demand_level, func.count(Prediction.id)).group_by(Prediction.demand_level).all()
                        
                        labels = ['Low', 'Medium', 'High', 'Critical']
                        d_tele = {l: 0 for l in labels}
                        idx_map = {'0': 'Low', '1': 'Medium', '2': 'High', '3': 'Critical'}
                        
                        for row in d_query:
                            k = str(row[0])
                            mk = idx_map.get(k, k)
                            if mk in d_tele: d_tele[mk] += int(row[1])
                            else: d_tele['Medium'] += int(row[1])

                        # Unified Neural Link Emission
                        socketio.emit('new_prediction', {
                            'stats': {'predictions': Prediction.query.count(), 'visitors': User.query.filter_by(role='visitor').count()},
                            'batch_log': f"[{time.strftime('%H:%M:%S')}] Neural Sync successful.",
                            'new_results': pred_data,
                            'zone_data': z_tele,
                            'demand_data': d_tele
                        }, namespace='/admin')

            except Exception as e:
                print(f"Neural Link Error: {e}")
            
            socketio.sleep(2) # Professionally sleep via SocketIO

    socketio.start_background_task(run_simulation)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", allow_credentials=True)
    login_manager.login_view = 'auth.login'

    from .auth.routes import auth
    from .admin.routes import admin
    from .staff.routes import staff
    from .developer.routes import developer
    from .visitor.routes import visitor

    app.register_blueprint(auth)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(staff, url_prefix='/staff')
    app.register_blueprint(developer, url_prefix='/developer')
    app.register_blueprint(visitor, url_prefix='/visitor')

    # Start the Zero-Touch Autopilot
    start_autopilot(app)

    return app
