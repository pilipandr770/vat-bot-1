from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os

db = SQLAlchemy()

# Определяем схему из переменной окружения
SCHEMA = os.environ.get('DB_SCHEMA', 'public')

class Company(db.Model):
    """Requester company data (left column in UI)."""
    __tablename__ = 'companies'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id'), nullable=True, index=True)
    vat_number = db.Column(db.String(20), nullable=False, index=True)
    company_name = db.Column(db.String(255), nullable=False)
    legal_address = db.Column(db.Text, nullable=False)
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    verification_checks = db.relationship('VerificationCheck', backref='company', lazy=True)
    
    def __repr__(self):
        return f'<Company {self.company_name} ({self.vat_number})>'

class Counterparty(db.Model):
    """Target verification company (middle column in UI)."""
    __tablename__ = 'counterparties'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id'), nullable=True, index=True)
    vat_number = db.Column(db.String(20), nullable=True, index=True)
    company_name = db.Column(db.String(255), nullable=False, index=True)
    address = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(255), nullable=True)
    domain = db.Column(db.String(255), nullable=True)
    contact_person = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(5), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    verification_checks = db.relationship('VerificationCheck', backref='counterparty', lazy=True)
    
    def __repr__(self):
        return f'<Counterparty {self.company_name} ({self.country})>'

class VerificationCheck(db.Model):
    """Individual verification session."""
    __tablename__ = 'verification_checks'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id'), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.companies.id'), nullable=False)
    counterparty_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.counterparties.id'), nullable=False)
    check_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    overall_status = db.Column(db.String(20), nullable=False)  # valid, warning, error
    confidence_score = db.Column(db.Float, default=0.0)
    is_monitoring_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    check_results = db.relationship('CheckResult', backref='verification_check', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<VerificationCheck {self.id} - {self.overall_status}>'
    
    def get_latest_results(self):
        """Get latest results grouped by service."""
        results = {}
        for result in self.check_results:
            if result.service_name not in results or result.created_at > results[result.service_name].created_at:
                results[result.service_name] = result
        return results

class CheckResult(db.Model):
    """Results from each verification service."""
    __tablename__ = 'check_results'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.verification_checks.id'), nullable=False)
    service_name = db.Column(db.String(50), nullable=False, index=True)  # vies, handelsregister, sanctions, etc.
    status = db.Column(db.String(20), nullable=False)  # valid, warning, error
    confidence_score = db.Column(db.Float, default=0.0)
    data_json = db.Column(db.Text, nullable=True)  # Raw API response data
    error_message = db.Column(db.Text, nullable=True)
    response_time_ms = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<CheckResult {self.service_name} - {self.status}>'
    
    @property
    def data(self):
        """Parse JSON data."""
        if self.data_json:
            try:
                return json.loads(self.data_json)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @data.setter
    def data(self, value):
        """Set JSON data."""
        if value:
            self.data_json = json.dumps(value)
        else:
            self.data_json = None

class Alert(db.Model):
    """Monitoring alerts for status changes."""
    __tablename__ = 'alerts'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    check_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.verification_checks.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # sanctions_found, insolvency_started, vat_invalid, etc.
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high, critical
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    verification_check = db.relationship('VerificationCheck', backref='alerts')
    
    def __repr__(self):
        return f'<Alert {self.alert_type} - {self.severity}>'