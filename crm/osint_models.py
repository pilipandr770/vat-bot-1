# FILE: crm/osint_models.py
from datetime import datetime
import json
import os
from .models import db, SCHEMA


class OsintScan(db.Model):
    __tablename__ = "osint_scans"
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(512), nullable=True)
    domain = db.Column(db.String(255), nullable=True, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    findings = db.relationship("OsintFinding", backref="scan", lazy=True, cascade="all, delete-orphan")


class OsintFinding(db.Model):
    __tablename__ = "osint_findings"
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey(f"{SCHEMA}.osint_scans.id"), nullable=False, index=True)
    service = db.Column(db.String(64), nullable=False)  # whois/dns/ssl_labs/...
    status = db.Column(db.String(16), nullable=False)   # ok/warn/error
    notes = db.Column(db.Text, nullable=True)
    data_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    @property
    def data(self):
        try:
            return json.loads(self.data_json) if self.data_json else {}
        except Exception:
            return {}

    @data.setter
    def data(self, value):
        self.data_json = json.dumps(value, ensure_ascii=False) if value else None
