"""
Legal pages routes: Impressum, Datenschutz, AGB, Data Deletion
Compliant with EU GDPR and German law (TMG, DSGVO)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from crm.models import db
from auth.models import User, Subscription, Payment
from datetime import datetime
import logging

legal_bp = Blueprint('legal', __name__)
logger = logging.getLogger(__name__)


@legal_bp.route('/impressum')
def impressum():
    """Impressum (Legal Notice) - Required by German law (§5 TMG)."""
    return render_template('legal/impressum.html')


@legal_bp.route('/datenschutz')
def datenschutz():
    """Datenschutzerklärung (Privacy Policy) - Required by GDPR."""
    return render_template('legal/datenschutz.html')


@legal_bp.route('/agb')
def agb():
    """Allgemeine Geschäftsbedingungen (Terms and Conditions)."""
    return render_template('legal/agb.html')


@legal_bp.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    """
    GDPR Right to Erasure (Art. 17 GDPR)
    Allow users to request deletion of their personal data.
    """
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_text = request.form.get('confirm_text')
        
        # Security check: verify password
        if not current_user.check_password(password):
            flash('Falsches Passwort. Datenlöschung abgebrochen.', 'error')
            return redirect(url_for('legal.delete_account'))
        
        # Confirmation check
        if confirm_text != 'LÖSCHEN':
            flash('Bitte geben Sie "LÖSCHEN" ein, um fortzufahren.', 'error')
            return redirect(url_for('legal.delete_account'))
        
        try:
            user_email = current_user.email
            user_id = current_user.id
            
            # Log deletion request for compliance
            logger.info(f"GDPR Data Deletion Request: User ID {user_id}, Email: {user_email}")
            
            # Delete all related data according to GDPR
            # This ensures complete data erasure as required by Art. 17 GDPR
            
            # 1. Delete user's verification checks and results
            from crm.models import VerificationCheck, CheckResult, Alert
            checks = VerificationCheck.query.filter_by(user_id=user_id).all()
            for check in checks:
                # Delete check results
                CheckResult.query.filter_by(check_id=check.id).delete()
                # Delete alerts
                Alert.query.filter_by(check_id=check.id).delete()
                # Delete check itself
                db.session.delete(check)
            
            # 2. Delete user's companies and counterparties
            from crm.models import Company, Counterparty
            Company.query.filter_by(user_id=user_id).delete()
            Counterparty.query.filter_by(user_id=user_id).delete()
            
            # 3. Delete subscription data
            Subscription.query.filter_by(user_id=user_id).delete()
            
            # 4. Delete payment records (anonymize for accounting compliance)
            # Note: For German tax law, we must keep payment records for 10 years
            # but we anonymize personal data
            payments = Payment.query.filter_by(user_id=user_id).all()
            for payment in payments:
                payment.user_id = None  # Anonymize instead of delete
                payment.customer_email = f"deleted_user_{user_id}@anonymized.local"
            
            # 5. Delete the user account
            db.session.delete(current_user)
            
            # Commit all deletions
            db.session.commit()
            
            # Log successful deletion for compliance
            logger.info(f"GDPR Data Deletion Completed: Former User ID {user_id}, Email: {user_email}")
            
            # Logout and redirect to confirmation page
            from flask_login import logout_user
            logout_user()
            
            flash('Ihr Konto und alle persönlichen Daten wurden erfolgreich gelöscht.', 'success')
            return redirect(url_for('legal.deletion_confirmed'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during data deletion for user {current_user.id}: {str(e)}")
            flash('Ein Fehler ist aufgetreten. Bitte kontaktieren Sie den Support.', 'error')
            return redirect(url_for('legal.delete_account'))
    
    return render_template('legal/delete_account.html')


@legal_bp.route('/deletion-confirmed')
def deletion_confirmed():
    """Confirmation page after successful account deletion."""
    return render_template('legal/deletion_confirmed.html')


@legal_bp.route('/gdpr-request', methods=['GET', 'POST'])
def gdpr_request():
    """
    GDPR Data Access Request (Art. 15 GDPR)
    Allow anyone to request information about their stored data.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        request_type = request.form.get('request_type')
        message = request.form.get('message')
        
        # Log the request for compliance
        logger.info(f"GDPR Request received: Type={request_type}, Email={email}")
        
        # In production, this would send an email to the data protection officer
        # For now, we just show a confirmation message
        
        flash('Ihre Anfrage wurde erhalten. Wir werden Sie innerhalb von 30 Tagen kontaktieren, wie es die DSGVO vorschreibt.', 'success')
        return redirect(url_for('legal.gdpr_request'))
    
    return render_template('legal/gdpr_request.html')
