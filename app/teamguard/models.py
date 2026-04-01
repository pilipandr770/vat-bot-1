"""
TeamGuard Models — Team security management for SMBs.

Tables:
  - TeamMember          : Employee/team member record with role and access level
  - PasswordPolicy      : Per-company password rotation policy
  - PasswordAssignment  : Secure generated password record per member
  - SecurityEvent       : Audit log (login, password change, offboarding, etc.)
  - PhishingTest        : Admin-created phishing awareness tests
  - PhishingClick       : Tracking record for each click/open of a phishing test
"""

import os
import json
from datetime import datetime

from crm.models import db

SCHEMA = os.environ.get('DB_SCHEMA', 'public')


class TeamMember(db.Model):
    """Employee or team member managed by company admin."""
    __tablename__ = 'teamguard_members'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    # The company admin who manages this member (User.id)
    owner_user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'),
                              nullable=False, index=True)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    position = db.Column(db.String(200), nullable=True)   # Job title / role description

    # Access level: owner > admin > manager > employee > guest
    access_level = db.Column(
        db.String(20),
        nullable=False,
        default='employee'
    )

    # When the password was last changed (manually tracked or auto-updated)
    password_last_changed = db.Column(db.DateTime, nullable=True)

    # Days before admin is notified to request a password change
    password_rotation_days = db.Column(db.Integer, nullable=True)  # None = use policy default

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    password_assignments = db.relationship(
        'PasswordAssignment', backref='member', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    security_events = db.relationship(
        'SecurityEvent', backref='member', lazy='dynamic',
        cascade='all, delete-orphan'
    )
    phishing_clicks = db.relationship(
        'PhishingClick', backref='member', lazy='dynamic',
        cascade='all, delete-orphan'
    )

    @property
    def days_since_password_change(self):
        if not self.password_last_changed:
            return None
        delta = datetime.utcnow() - self.password_last_changed
        return delta.days

    @property
    def password_expired(self):
        """Returns True if password rotation is overdue according to assigned or policy days."""
        days = self.days_since_password_change
        rotation = self.password_rotation_days
        if days is None or rotation is None:
            return False
        return days >= rotation

    def __repr__(self):
        return f'<TeamMember {self.email} [{self.access_level}]>'


ACCESS_LEVELS = ['owner', 'admin', 'manager', 'employee', 'guest']

ACCESS_LEVEL_LABELS = {
    'owner': 'Eigentümer',
    'admin': 'Administrator',
    'manager': 'Manager',
    'employee': 'Mitarbeiter',
    'guest': 'Gast',
}


class PasswordPolicy(db.Model):
    """Company-level password rotation policy."""
    __tablename__ = 'teamguard_password_policy'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'),
                              nullable=False, unique=True, index=True)

    # Rotation frequency in days; 0 = rotation disabled
    rotation_days = db.Column(db.Integer, default=90, nullable=False)

    # Minimum password length
    min_length = db.Column(db.Integer, default=12, nullable=False)

    # Require at least one: uppercase, digit, special char
    require_uppercase = db.Column(db.Boolean, default=True)
    require_digit = db.Column(db.Boolean, default=True)
    require_special = db.Column(db.Boolean, default=True)

    # Send email reminder N days before expiry
    reminder_days_before = db.Column(db.Integer, default=7, nullable=False)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PasswordPolicy owner={self.owner_user_id} rotation={self.rotation_days}d>'


class PasswordAssignment(db.Model):
    """
    Record of a secure generated password sent to a team member.
    Passwords are NOT stored in plaintext — only metadata and a hash.
    The generated password is sent via email then discarded.
    """
    __tablename__ = 'teamguard_password_assignments'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.teamguard_members.id', ondelete='CASCADE'),
                          nullable=False, index=True)

    # SHA-256 hash of generated password for audit purposes (not for authentication)
    password_hash = db.Column(db.String(64), nullable=True)

    sent_via = db.Column(db.String(20), default='email')  # 'email' | 'sms' (future)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_by_user_id = db.Column(db.Integer, nullable=True)  # admin who triggered

    # Member confirmed receipt
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<PasswordAssignment member={self.member_id} sent={self.sent_at}>'


class SecurityEvent(db.Model):
    """Audit log for security-relevant events per team member."""
    __tablename__ = 'teamguard_security_events'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.teamguard_members.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    owner_user_id = db.Column(db.Integer, nullable=False, index=True)

    # Event types: password_reset | password_reminder | onboarding | offboarding
    #              access_changed | phishing_click | message_sent | manual_note
    event_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    performed_by = db.Column(db.String(200), nullable=True)  # admin email
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f'<SecurityEvent {self.event_type} member={self.member_id}>'


EVENT_TYPE_LABELS = {
    'password_reset': 'Passwort generiert & gesendet',
    'password_reminder': 'Passwort-Erinnerung gesendet',
    'onboarding': 'Mitarbeiter hinzugefügt',
    'offboarding': 'Mitarbeiter deaktiviert',
    'access_changed': 'Zugriffsebene geändert',
    'phishing_click': 'Phishing-Test angeklickt ⚠️',
    'phishing_ignored': 'Phishing-Test bestanden ✅',
    'message_sent': 'Nachricht gesendet',
    'manual_note': 'Manuelle Notiz',
}


class PhishingTest(db.Model):
    """
    Admin-created phishing awareness test.

    SECURITY NOTE: This feature is strictly limited to the company admin's
    own team members only. It is an internal security awareness tool,
    NOT a general phishing tool. All tests are logged and auditable.
    """
    __tablename__ = 'teamguard_phishing_tests'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id', ondelete='CASCADE'),
                              nullable=False, index=True)

    name = db.Column(db.String(200), nullable=False)         # Test name (internal)
    subject_line = db.Column(db.String(300), nullable=False) # Fake email subject

    # Template type: 'link_click' | 'attachment' | 'credential_harvest' (simulated only)
    template_type = db.Column(db.String(30), default='link_click', nullable=False)

    # Unique token used in the tracking URL
    tracking_token = db.Column(db.String(64), unique=True, nullable=False, index=True)

    # Comma-separated member IDs who received the test
    sent_to_member_ids_json = db.Column(db.Text, nullable=True)   # JSON list

    status = db.Column(db.String(20), default='draft')  # draft | sent | completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    clicks = db.relationship('PhishingClick', backref='test', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def sent_to_member_ids(self):
        if self.sent_to_member_ids_json:
            try:
                return json.loads(self.sent_to_member_ids_json)
            except Exception:
                return []
        return []

    @sent_to_member_ids.setter
    def sent_to_member_ids(self, value):
        self.sent_to_member_ids_json = json.dumps(value or [])

    @property
    def total_sent(self):
        return len(self.sent_to_member_ids)

    @property
    def total_clicks(self):
        return self.clicks.count()

    @property
    def click_rate(self):
        if not self.total_sent:
            return 0
        return round(self.total_clicks / self.total_sent * 100)

    def __repr__(self):
        return f'<PhishingTest "{self.name}" clicks={self.total_clicks}/{self.total_sent}>'


class PhishingClick(db.Model):
    """Recorded when a team member clicks a phishing test link."""
    __tablename__ = 'teamguard_phishing_clicks'
    __table_args__ = {'schema': SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.teamguard_phishing_tests.id', ondelete='CASCADE'),
                        nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.teamguard_members.id', ondelete='CASCADE'),
                          nullable=False, index=True)

    clicked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    # Hashed IP for basic analytics — never store raw IP
    ip_hash = db.Column(db.String(64), nullable=True)
    user_agent_snippet = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<PhishingClick test={self.test_id} member={self.member_id}>'
