"""
Authentication routes for user registration, login, and password management.
All text in German (Deutsche).
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
try:
    from werkzeug.urls import url_parse
except ImportError:
    from urllib.parse import urlparse as url_parse
from datetime import datetime
from auth.models import User, Subscription
from auth.forms import (RegistrationForm, LoginForm, PasswordResetRequestForm, 
                        PasswordResetForm, ProfileUpdateForm, ChangePasswordForm, DeleteAccountForm)
from crm.models import db
from notifications.alerts import send_email
import secrets

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registrierungsseite - User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            # Create new user
            user = User(
                email=form.email.data.lower().strip(),
                company_name=form.company_name.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
                phone=form.phone.data,
                country=form.country.data
            )
            user.set_password(form.password.data)
            # TEST MODE: Email confirmation disabled - automatically confirm email
            user.is_email_confirmed = True
            # user.generate_confirmation_token()  # Disabled for testing
            
            db.session.add(user)
            db.session.commit()
            
            # Create basic (trial) subscription for new user
            # User gets 3-day free trial before being charged
            trial_subscription = Subscription(
                user_id=user.id,
                plan='basic',
                status='active',
                api_calls_limit=100,  # Basic plan limit
                monthly_price=9.99,
                api_calls_used=0
            )
            db.session.add(trial_subscription)
            # send_confirmation_email(user)  # Disabled for testing
            
            flash('Registrierung erfolgreich! Sie können sich jetzt anmelden.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Registration error: {str(e)}')
            flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.', 'error')
    
    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Anmeldeseite - User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        
        if user is None or not user.check_password(form.password.data):
            flash('Ungültige E-Mail-Adresse oder Passwort.', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Ihr Konto wurde deaktiviert. Bitte kontaktieren Sie den Support.', 'error')
            return redirect(url_for('auth.login'))
        
        # TEST MODE: Email confirmation check disabled
        # if not user.is_email_confirmed:
        #     flash('Bitte bestätigen Sie Ihre E-Mail-Adresse. Bestätigungs-E-Mail wurde erneut gesendet.', 'warning')
        #     send_confirmation_email(user)
        #     return redirect(url_for('auth.login'))
        
        # Login successful
        login_user(user, remember=form.remember_me.data)
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('dashboard')
        
        flash(f'Willkommen zurück, {user.first_name}!', 'success')
        return redirect(next_page)
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Abmelden - User logout."""
    logout_user()
    flash('Sie wurden erfolgreich abgemeldet.', 'info')
    return redirect(url_for('landing'))


@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    """E-Mail-Bestätigung - Email confirmation."""
    if current_user.is_authenticated and current_user.is_email_confirmed:
        return redirect(url_for('dashboard'))
    
    user = User.query.filter_by(email_confirmation_token=token).first()
    
    if user is None:
        flash('Ungültiger Bestätigungslink.', 'error')
        return redirect(url_for('auth.login'))
    
    if user.confirm_email(token):
        db.session.commit()
        flash('Ihre E-Mail-Adresse wurde erfolgreich bestätigt! Sie können sich jetzt anmelden.', 'success')
        return redirect(url_for('auth.login'))
    else:
        flash('Ungültiger oder abgelaufener Bestätigungslink.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/resend-confirmation')
@login_required
def resend_confirmation():
    """Bestätigungs-E-Mail erneut senden - Resend confirmation email."""
    if current_user.is_email_confirmed:
        flash('Ihre E-Mail-Adresse ist bereits bestätigt.', 'info')
        return redirect(url_for('dashboard'))
    
    send_confirmation_email(current_user)
    flash('Bestätigungs-E-Mail wurde erneut gesendet. Bitte überprüfen Sie Ihren Posteingang.', 'success')
    return redirect(url_for('dashboard'))


@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Passwort zurücksetzen anfordern - Request password reset."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = PasswordResetRequestForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        
        if user:
            token = generate_reset_token(user)
            send_password_reset_email(user, token)
        
        # Always show success message (security: don't reveal if email exists)
        flash('Wenn diese E-Mail-Adresse registriert ist, haben Sie eine E-Mail mit Anweisungen zum Zurücksetzen Ihres Passworts erhalten.', 'info')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Passwort zurücksetzen - Reset password with token."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    user = verify_reset_token(token)
    
    if not user:
        flash('Ungültiger oder abgelaufener Link zum Zurücksetzen des Passworts.', 'error')
        return redirect(url_for('auth.login'))
    
    form = PasswordResetForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Ihr Passwort wurde erfolgreich zurückgesetzt. Sie können sich jetzt anmelden.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Benutzerprofil - User profile page."""
    form = ProfileUpdateForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.company_name = form.company_name.data
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        current_user.country = form.country.data
        
        db.session.commit()
        flash('Ihr Profil wurde erfolgreich aktualisiert.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html', form=form)


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Passwort ändern - Change password for authenticated users."""
    form = ChangePasswordForm()

    if form.validate_on_submit():
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Ihr Passwort wurde erfolgreich aktualisiert.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/change_password.html', form=form)


@auth_bp.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    """Konto löschen - DSGVO-konforme Profilentfernung."""
    form = DeleteAccountForm()

    if form.validate_on_submit():
        user = current_user
        user_id = user.id

        # Lazy imports to avoid circular dependencies
        from crm.models import Company, Counterparty, VerificationCheck, Alert, CheckResult
        try:
            from app.mailguard.models import MailAccount, MailMessage, MailDraft, ScanReport
        except ImportError:
            MailAccount = MailMessage = MailDraft = ScanReport = None  # MailGuard optional

        try:
            # MailGuard cleanup (if module available)
            if MailAccount:
                accounts = MailAccount.query.filter_by(user_id=user_id).all()
                for account in accounts:
                    message_ids = [mid for (mid,) in db.session.query(MailMessage.id).filter_by(account_id=account.id).all()]
                    if message_ids:
                        db.session.query(ScanReport).filter(ScanReport.message_id.in_(message_ids)).delete(synchronize_session=False)
                        db.session.query(MailDraft).filter(MailDraft.message_id.in_(message_ids)).delete(synchronize_session=False)
                        db.session.query(MailMessage).filter(MailMessage.id.in_(message_ids)).delete(synchronize_session=False)
                    db.session.query(MailDraft).filter_by(account_id=account.id).delete(synchronize_session=False)
                    db.session.delete(account)

            # Verification history cleanup
            verification_ids = [vid for (vid,) in db.session.query(VerificationCheck.id).filter_by(user_id=user_id).all()]
            if verification_ids:
                db.session.query(CheckResult).filter(CheckResult.check_id.in_(verification_ids)).delete(synchronize_session=False)
                db.session.query(Alert).filter(Alert.check_id.in_(verification_ids)).delete(synchronize_session=False)
                db.session.query(VerificationCheck).filter(VerificationCheck.id.in_(verification_ids)).delete(synchronize_session=False)

            # Related company data
            db.session.query(Company).filter_by(user_id=user_id).delete(synchronize_session=False)
            db.session.query(Counterparty).filter_by(user_id=user_id).delete(synchronize_session=False)

            # Subscription, payments cascade via relationships on User
            logout_user()
            db.session.delete(user)
            db.session.commit()
            flash('Ihr Konto und alle zugehörigen Daten wurden gelöscht. Wir bedauern, Sie zu verlieren.', 'success')
            return redirect(url_for('landing'))
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(f'Account deletion failed for user {user_id}: {exc}')
            flash('Beim Löschen Ihres Kontos ist ein Fehler aufgetreten. Bitte wenden Sie sich an den Support.', 'error')

    return render_template('auth/delete_account.html', form=form)


@auth_bp.route('/company-profile', methods=['GET', 'POST'])
@login_required
def company_profile():
    """Firmenprofil - Company profile page for automatic form filling."""
    if request.method == 'POST':
        # Get form data
        current_user.company_name = request.form.get('company_name', '').strip()
        current_user.company_vat_number = request.form.get('company_vat_number', '').strip()
        current_user.country = request.form.get('country', '').strip()
        current_user.company_email = request.form.get('company_email', '').strip()
        current_user.company_address = request.form.get('company_address', '').strip()
        current_user.company_phone = request.form.get('company_phone', '').strip()
        
        # If all required fields are empty, user wants to delete profile
        if not current_user.company_vat_number:
            current_user.company_name = None
            current_user.company_vat_number = None
            current_user.company_address = None
            current_user.company_email = None
            current_user.company_phone = None
            flash('Ihr Firmenprofil wurde gelöscht.', 'success')
        else:
            flash('Ihr Firmenprofil wurde erfolgreich gespeichert!', 'success')
        
        db.session.commit()
        return redirect(url_for('auth.company_profile'))
    
    return render_template('auth/company_profile.html')


# Helper functions

def send_confirmation_email(user):
    """Send email confirmation link to user."""
    if not user.email_confirmation_token:
        user.generate_confirmation_token()
        db.session.commit()
    
    confirm_url = url_for('auth.confirm_email', 
                         token=user.email_confirmation_token, 
                         _external=True)
    
    subject = 'Bestätigen Sie Ihre E-Mail-Adresse - VAT Verifizierung'
    
    html_body = f"""
    <html>
        <body>
            <h2>Willkommen bei VAT Verifizierung!</h2>
            <p>Hallo {user.first_name},</p>
            <p>Vielen Dank für Ihre Registrierung. Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den Link unten klicken:</p>
            <p><a href="{confirm_url}" style="background-color: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">E-Mail bestätigen</a></p>
            <p>Oder kopieren Sie diesen Link in Ihren Browser:</p>
            <p>{confirm_url}</p>
            <p>Wenn Sie diese E-Mail nicht angefordert haben, können Sie sie ignorieren.</p>
            <br>
            <p>Mit freundlichen Grüßen,<br>Ihr VAT Verifizierung Team</p>
        </body>
    </html>
    """
    
    text_body = f"""
    Willkommen bei VAT Verifizierung!
    
    Hallo {user.first_name},
    
    Vielen Dank für Ihre Registrierung. Bitte bestätigen Sie Ihre E-Mail-Adresse, indem Sie auf den folgenden Link klicken:
    
    {confirm_url}
    
    Wenn Sie diese E-Mail nicht angefordert haben, können Sie sie ignorieren.
    
    Mit freundlichen Grüßen,
    Ihr VAT Verifizierung Team
    """
    
    send_email(
        subject=subject,
        recipient=user.email,
        text_body=text_body,
        html_body=html_body
    )


def generate_reset_token(user):
    """Generate password reset token."""
    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    return token


def verify_reset_token(token):
    """Verify password reset token."""
    from datetime import timedelta
    
    user = User.query.filter_by(password_reset_token=token).first()
    
    if user and user.password_reset_expires > datetime.utcnow():
        return user
    
    return None


def send_password_reset_email(user, token):
    """Send password reset email."""
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    subject = 'Passwort zurücksetzen - VAT Verifizierung'
    
    html_body = f"""
    <html>
        <body>
            <h2>Passwort zurücksetzen</h2>
            <p>Hallo {user.first_name},</p>
            <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt. Klicken Sie auf den Link unten, um ein neues Passwort zu erstellen:</p>
            <p><a href="{reset_url}" style="background-color: #0d6efd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Passwort zurücksetzen</a></p>
            <p>Oder kopieren Sie diesen Link in Ihren Browser:</p>
            <p>{reset_url}</p>
            <p><strong>Dieser Link ist 24 Stunden gültig.</strong></p>
            <p>Wenn Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.</p>
            <br>
            <p>Mit freundlichen Grüßen,<br>Ihr VAT Verifizierung Team</p>
        </body>
    </html>
    """
    
    text_body = f"""
    Passwort zurücksetzen
    
    Hallo {user.first_name},
    
    Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt. Besuchen Sie den folgenden Link, um ein neues Passwort zu erstellen:
    
    {reset_url}
    
    Dieser Link ist 24 Stunden gültig.
    
    Wenn Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.
    
    Mit freundlichen Grüßen,
    Ihr VAT Verifizierung Team
    """
    
    send_email(
        subject=subject,
        recipient=user.email,
        text_body=text_body,
        html_body=html_body
    )


# Add missing fields to User model for password reset
from datetime import timedelta

# These will be added to auth/models.py:
# password_reset_token = db.Column(db.String(100), unique=True)
# password_reset_expires = db.Column(db.DateTime)
