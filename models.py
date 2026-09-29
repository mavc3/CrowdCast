from . import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'staff', 'developer', 'visitor'), default='visitor')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemLog(db.Model):
    __tablename__ = 'system_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action_type = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    user = db.relationship('User', backref='logs')

class Stadium(db.Model):
    __tablename__ = 'stadiums'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255))
    capacity = db.Column(db.Integer)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))

class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    stadium_id = db.Column(db.Integer, db.ForeignKey('stadiums.id'))
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(100))
    capacity = db.Column(db.Integer)
    operating_hours = db.Column(db.String(255))
    status = db.Column(db.String(50), default='Open')
    location = db.Column(db.String(255))
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    stadium = db.relationship('Stadium', backref='services')

class PredictionBatch(db.Model):
    __tablename__ = 'prediction_batches'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    records_count = db.Column(db.Integer, default=0)
    user = db.relationship('User', backref='batches')

class Prediction(db.Model):
    __tablename__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('prediction_batches.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expected_visitors = db.Column(db.Integer)
    demand_level = db.Column(db.String(50))
    waiting_time = db.Column(db.Integer, default=15)
    batch = db.relationship('PredictionBatch', backref='results')
    service = db.relationship('Service', backref='predictions')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Visit(db.Model):
    __tablename__ = 'visits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    duration = db.Column(db.Integer, default=30) # Average visit in minutes
    
    user = db.relationship('User', backref='visits')
    service = db.relationship('Service', backref='visits')

class OperationalData(db.Model):
    __tablename__ = 'operational_data'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    waiting_time = db.Column(db.Integer) # in minutes
    current_capacity = db.Column(db.Integer)
    availability_status = db.Column(db.String(50)) # Available, Busy, Closed
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    service = db.relationship('Service', backref='operational_history')

class TicketSales(db.Model):
    __tablename__ = 'ticket_sales'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)
    visitor_count = db.Column(db.Integer, default=0)
    ticket_count = db.Column(db.Integer, default=0)
    service = db.relationship('Service', backref='sales_records')

class PredictionResult(db.Model):
    __tablename__ = 'prediction_results'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    date = db.Column(db.Date, nullable=False)
    hour = db.Column(db.Integer, nullable=False)
    predicted_visitors = db.Column(db.Integer)
    crowd_level = db.Column(db.String(50)) # Low, Medium, High
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    service = db.relationship('Service', backref='result_history')

class ModelRegistry(db.Model):
    __tablename__ = 'model_registry'
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(255), nullable=False)
    model_type = db.Column(db.String(100)) # Classifier, Regressor
    version = db.Column(db.String(50))
    status = db.Column(db.String(50), default='Active')
    loaded_at = db.Column(db.DateTime, default=datetime.utcnow)
