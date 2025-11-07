from crm.models import db
from datetime import datetime, time
import json
from sqlalchemy import Enum
import os

# Определяем схему из переменной окружения
SCHEMA = os.environ.get('DB_SCHEMA', 'public')

# Импортируем User для правильной работы ForeignKey
# Это необходимо, чтобы SQLAlchemy мог найти таблицу users в метаданных
from auth.models import User

class MailAccount(db.Model):
    """Почтовые аккаунты пользователей"""
    __tablename__ = 'mail_account'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.users.id'), nullable=False)
    provider = db.Column(Enum('gmail', 'outlook', 'imap', name='provider_types', schema=SCHEMA), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text, nullable=True)  # Зашифрованный
    refresh_token = db.Column(db.Text, nullable=True)  # Зашифрованный
    expires_at = db.Column(db.DateTime, nullable=True)
    host = db.Column(db.String(255), nullable=True)  # Для IMAP
    port = db.Column(db.Integer, nullable=True)  # Для IMAP
    login = db.Column(db.String(255), nullable=True)  # Для IMAP
    password = db.Column(db.Text, nullable=True)  # Зашифрованный, для IMAP
    settings_json = db.Column(db.Text, default='{}')  # JSON с настройками
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    messages = db.relationship('MailMessage', backref='account', lazy=True)
    drafts = db.relationship('MailDraft', backref='account', lazy=True)

    def get_settings(self):
        return json.loads(self.settings_json) if self.settings_json else {}

    def set_settings(self, settings):
        self.settings_json = json.dumps(settings)

class KnownCounterparty(db.Model):
    """Известные контрагенты"""
    __tablename__ = 'known_counterparty'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    priority = db.Column(db.Integer, default=0)  # 0=normal, 1=high, 2=vip
    assistant_profile_id = db.Column(db.String(100), nullable=True)  # ID профиля ассистента
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    messages = db.relationship('MailMessage', backref='counterparty', lazy=True)

class MailRule(db.Model):
    """Правила обработки почты"""
    __tablename__ = 'mail_rule'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    match_from = db.Column(db.String(255), nullable=True)  # Конкретный email
    match_domain = db.Column(db.String(255), nullable=True)  # Домен или '*' для всех
    match_subject_regex = db.Column(db.String(500), nullable=True)  # Регулярка для темы
    action = db.Column(Enum('auto_reply', 'draft', 'quarantine', 'ignore', name='action_types', schema=SCHEMA), default='draft')
    requires_human = db.Column(db.Boolean, default=True)
    workhours_json = db.Column(db.Text, default='{}')  # JSON с рабочими часами
    priority = db.Column(db.Integer, default=0)  # Приоритет применения правила
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_workhours(self):
        return json.loads(self.workhours_json) if self.workhours_json else {}

    def set_workhours(self, workhours):
        self.workhours_json = json.dumps(workhours)

    def matches(self, message):
        """Проверяет, подходит ли правило к сообщению"""
        if self.match_from and message.get('from_email') != self.match_from:
            return False
        if self.match_domain and self.match_domain != '*' and not message.get('from_email', '').endswith('@' + self.match_domain):
            return False
        if self.match_subject_regex:
            import re
            if not re.search(self.match_subject_regex, message.get('subject', ''), re.IGNORECASE):
                return False
        return True

class MailMessage(db.Model):
    """Входящие сообщения"""
    __tablename__ = 'mail_message'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    provider_msg_id = db.Column(db.String(255), unique=True, nullable=False)
    thread_id = db.Column(db.String(255), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.mail_account.id'), nullable=False)
    counterparty_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.known_counterparty.id'), nullable=True)
    from_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    received_at = db.Column(db.DateTime, nullable=False)
    risk_score = db.Column(db.Integer, default=0)  # 0-100
    status = db.Column(Enum('new', 'scanned', 'drafted', 'sent', 'quarantined', 'skipped', name='status_types', schema=SCHEMA), default='new')
    labels = db.Column(db.String(500), nullable=True)  # JSON с метками
    meta_json = db.Column(db.Text, default='{}')  # Дополнительные метаданные
    
    # Attachment security fields
    attachments_json = db.Column(db.Text, default='[]')  # JSON array с вложениями + scan results
    has_attachments = db.Column(db.Boolean, default=False)
    has_dangerous_attachments = db.Column(db.Boolean, default=False)
    is_quarantined = db.Column(db.Boolean, default=False)
    quarantine_reason = db.Column(db.String(500), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связи
    drafts = db.relationship('MailDraft', backref='message', lazy=True)
    scan_reports = db.relationship('ScanReport', backref='message', lazy=True)

    def get_meta(self):
        return json.loads(self.meta_json) if self.meta_json else {}

    def set_meta(self, meta):
        self.meta_json = json.dumps(meta)
    
    def get_attachments(self):
        """Получить список вложений с результатами сканирования"""
        return json.loads(self.attachments_json) if self.attachments_json else []
    
    def set_attachments(self, attachments):
        """Сохранить вложения с результатами сканирования"""
        self.attachments_json = json.dumps(attachments)
        self.has_attachments = len(attachments) > 0
        
        # Проверяем наличие опасных вложений
        self.has_dangerous_attachments = any(
            att.get('risk_level') == 'danger' for att in attachments
        )
        
        # Автоматически помещаем в карантин если есть опасные вложения
        if self.has_dangerous_attachments:
            self.is_quarantined = True
            dangerous_files = [att['filename'] for att in attachments if att.get('risk_level') == 'danger']
            self.quarantine_reason = f"Опасные вложения: {', '.join(dangerous_files)}"
            self.status = 'quarantined'

class MailDraft(db.Model):
    """Черновики ответов"""
    __tablename__ = 'mail_draft'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.mail_message.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.mail_account.id'), nullable=False)
    to_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    body_html = db.Column(db.Text, nullable=True)
    body_text = db.Column(db.Text, nullable=True)
    attachments_json = db.Column(db.Text, default='[]')  # JSON с вложениями
    suggested_by = db.Column(Enum('assistant', 'rule', 'manual', name='suggested_by_types', schema=SCHEMA), default='assistant')
    approved_by_user = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_attachments(self):
        return json.loads(self.attachments_json) if self.attachments_json else []

    def set_attachments(self, attachments):
        self.attachments_json = json.dumps(attachments)

class ScanReport(db.Model):
    """Отчёты сканирования"""
    __tablename__ = 'scan_report'
    __table_args__ = {'schema': SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.Integer, db.ForeignKey(f'{SCHEMA}.mail_message.id'), nullable=False)
    verdict = db.Column(Enum('safe', 'suspicious', 'malicious', name='verdict_types', schema=SCHEMA), nullable=False)
    score = db.Column(db.Integer, nullable=False)  # 0-100
    details_json = db.Column(db.Text, default='{}')  # Детали сканирования
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_details(self):
        return json.loads(self.details_json) if self.details_json else {}

    def set_details(self, details):
        self.details_json = json.dumps(details)