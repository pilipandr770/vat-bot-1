"""
Authentication forms for registration, login, and password reset.
German language forms using Flask-WTF.
"""

from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from auth.models import User


class RegistrationForm(FlaskForm):
    """Registrierungsformular."""
    
    email = StringField('E-Mail-Adresse', validators=[
        DataRequired(message='E-Mail ist erforderlich'),
        Email(message='Ungültige E-Mail-Adresse')
    ])
    
    company_name = StringField('Firmenname', validators=[
        DataRequired(message='Firmenname ist erforderlich'),
        Length(min=2, max=200, message='Firmenname muss zwischen 2 und 200 Zeichen lang sein')
    ])
    
    first_name = StringField('Vorname', validators=[
        DataRequired(message='Vorname ist erforderlich'),
        Length(min=2, max=100)
    ])
    
    last_name = StringField('Nachname', validators=[
        DataRequired(message='Nachname ist erforderlich'),
        Length(min=2, max=100)
    ])
    
    phone = StringField('Telefonnummer', validators=[
        Length(max=50)
    ])
    
    country = SelectField('Land', choices=[
        ('DE', 'Deutschland'),
        ('AT', 'Österreich'),
        ('CH', 'Schweiz'),
        ('NL', 'Niederlande'),
        ('FR', 'Frankreich'),
        ('IT', 'Italien'),
        ('ES', 'Spanien'),
        ('PL', 'Polen'),
        ('CZ', 'Tschechien'),
        ('GB', 'Großbritannien'),
        ('US', 'USA')
    ], validators=[DataRequired(message='Land ist erforderlich')])
    
    password = PasswordField('Passwort', validators=[
        DataRequired(message='Passwort ist erforderlich'),
        Length(min=8, message='Passwort muss mindestens 8 Zeichen lang sein')
    ])
    
    password_confirm = PasswordField('Passwort bestätigen', validators=[
        DataRequired(message='Passwortbestätigung ist erforderlich'),
        EqualTo('password', message='Passwörter müssen übereinstimmen')
    ])
    
    accept_terms = BooleanField('Ich akzeptiere die AGB und Datenschutzerklärung', validators=[
        DataRequired(message='Sie müssen die AGB akzeptieren')
    ])
    
    def validate_email(self, field):
        """Check if email already exists."""
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Diese E-Mail-Adresse ist bereits registriert.')


class LoginForm(FlaskForm):
    """Anmeldeformular."""
    
    email = StringField('E-Mail-Adresse', validators=[
        DataRequired(message='E-Mail ist erforderlich'),
        Email(message='Ungültige E-Mail-Adresse')
    ])
    
    password = PasswordField('Passwort', validators=[
        DataRequired(message='Passwort ist erforderlich')
    ])
    
    remember_me = BooleanField('Angemeldet bleiben')


class PasswordResetRequestForm(FlaskForm):
    """Formular für Passwort-Zurücksetzen-Anfrage."""
    
    email = StringField('E-Mail-Adresse', validators=[
        DataRequired(message='E-Mail ist erforderlich'),
        Email(message='Ungültige E-Mail-Adresse')
    ])
    
    def validate_email(self, field):
        """Check if email exists."""
        if not User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError('Diese E-Mail-Adresse ist nicht registriert.')


class PasswordResetForm(FlaskForm):
    """Formular zum Zurücksetzen des Passworts."""
    
    password = PasswordField('Neues Passwort', validators=[
        DataRequired(message='Passwort ist erforderlich'),
        Length(min=8, message='Passwort muss mindestens 8 Zeichen lang sein')
    ])
    
    password_confirm = PasswordField('Passwort bestätigen', validators=[
        DataRequired(message='Passwortbestätigung ist erforderlich'),
        EqualTo('password', message='Passwörter müssen übereinstimmen')
    ])


class ProfileUpdateForm(FlaskForm):
    """Formular zur Profilaktualisierung."""
    
    company_name = StringField('Firmenname', validators=[
        DataRequired(message='Firmenname ist erforderlich'),
        Length(min=2, max=200)
    ])
    
    first_name = StringField('Vorname', validators=[
        DataRequired(message='Vorname ist erforderlich'),
        Length(min=2, max=100)
    ])
    
    last_name = StringField('Nachname', validators=[
        DataRequired(message='Nachname ist erforderlich'),
        Length(min=2, max=100)
    ])
    
    phone = StringField('Telefonnummer', validators=[
        Length(max=50)
    ])
    
    country = SelectField('Land', choices=[
        ('DE', 'Deutschland'),
        ('AT', 'Österreich'),
        ('CH', 'Schweiz'),
        ('NL', 'Niederlande'),
        ('FR', 'Frankreich'),
        ('IT', 'Italien'),
        ('ES', 'Spanien'),
        ('PL', 'Polen'),
        ('CZ', 'Tschechien'),
        ('GB', 'Großbritannien'),
        ('US', 'USA')
    ])


class ChangePasswordForm(FlaskForm):
    """Formular zum Ändern des Passworts im eingeloggten Zustand."""

    current_password = PasswordField('Aktuelles Passwort', validators=[
        DataRequired(message='Bitte geben Sie Ihr aktuelles Passwort ein')
    ])

    new_password = PasswordField('Neues Passwort', validators=[
        DataRequired(message='Neues Passwort ist erforderlich'),
        Length(min=8, message='Das neue Passwort muss mindestens 8 Zeichen lang sein')
    ])

    new_password_confirm = PasswordField('Neues Passwort bestätigen', validators=[
        DataRequired(message='Bitte bestätigen Sie Ihr neues Passwort'),
        EqualTo('new_password', message='Die Passwörter stimmen nicht überein')
    ])

    def validate_current_password(self, field):
        if not current_user.is_authenticated or not current_user.check_password(field.data):
            raise ValidationError('Das aktuelle Passwort ist nicht korrekt.')

    def validate_new_password(self, field):
        if current_user.is_authenticated and current_user.check_password(field.data):
            raise ValidationError('Das neue Passwort darf nicht mit dem aktuellen Passwort übereinstimmen.')
