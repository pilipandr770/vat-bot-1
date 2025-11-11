import os
import requests
from flask import current_app, url_for, session, redirect, flash
import json
from datetime import datetime, timedelta
from cryptography.fernet import Fernet

from .models import db, MailAccount

# Шифрование токенов
def get_cipher():
    key = current_app.config.get('MAILGUARD_ENCRYPTION_KEY')
    if not key:
        key = Fernet.generate_key()
        current_app.config['MAILGUARD_ENCRYPTION_KEY'] = key
    return Fernet(key)

def encrypt_token(token):
    if not token:
        return None
    cipher = get_cipher()
    return cipher.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token):
    if not encrypted_token:
        return None
    cipher = get_cipher()
    return cipher.decrypt(encrypted_token.encode()).decode()

# Gmail OAuth
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly'
]

def get_gmail_auth_url():
    """Получить URL для авторизации Gmail"""
    client_id = current_app.config.get('GMAIL_CLIENT_ID')
    redirect_uri = url_for('mailguard.gmail_callback', _external=True)

    auth_url = (
        'https://accounts.google.com/o/oauth2/v2/auth?'
        f'client_id={client_id}&'
        'response_type=code&'
        f'scope={" ".join(GMAIL_SCOPES)}&'
        f'redirect_uri={redirect_uri}&'
        'access_type=offline&'
        'prompt=consent'
    )
    return auth_url

def exchange_gmail_code(code):
    """Обменять код авторизации на токены"""
    client_id = current_app.config.get('GMAIL_CLIENT_ID')
    client_secret = current_app.config.get('GMAIL_CLIENT_SECRET')
    redirect_uri = url_for('mailguard.gmail_callback', _external=True)

    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

def refresh_gmail_token(refresh_token):
    """Обновить access token через refresh token"""
    client_id = current_app.config.get('GMAIL_CLIENT_ID')
    client_secret = current_app.config.get('GMAIL_CLIENT_SECRET')

    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

def get_gmail_email(access_token):
    """Получить email пользователя через Gmail API"""
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(
        'https://www.googleapis.com/gmail/v1/users/me/profile',
        headers=headers
    )
    response.raise_for_status()
    return response.json().get('emailAddress')

# Microsoft OAuth
MS_SCOPES = [
    'https://graph.microsoft.com/Mail.ReadWrite',
    'https://graph.microsoft.com/Mail.Send',
    'https://graph.microsoft.com/User.Read'
]

def get_ms_auth_url():
    """Получить URL для авторизации Microsoft 365"""
    client_id = current_app.config.get('MS_CLIENT_ID')
    redirect_uri = url_for('mailguard.microsoft_callback', _external=True)
    tenant = current_app.config.get('MS_TENANT_ID', 'common')

    auth_url = (
        f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?'
        f'client_id={client_id}&'
        'response_type=code&'
        f'scope={" ".join(MS_SCOPES)}&'
        f'redirect_uri={redirect_uri}&'
        'access_type=offline&'
        'prompt=consent'
    )
    return auth_url

def exchange_ms_code(code):
    """Обменять код авторизации Microsoft на токены"""
    client_id = current_app.config.get('MS_CLIENT_ID')
    client_secret = current_app.config.get('MS_CLIENT_SECRET')
    redirect_uri = url_for('mailguard.microsoft_callback', _external=True)
    tenant = current_app.config.get('MS_TENANT_ID', 'common')

    token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

def refresh_ms_token(refresh_token):
    """Обновить access token Microsoft через refresh token"""
    client_id = current_app.config.get('MS_CLIENT_ID')
    client_secret = current_app.config.get('MS_CLIENT_SECRET')
    tenant = current_app.config.get('MS_TENANT_ID', 'common')

    token_url = f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }

    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

def create_or_update_account(user_id, provider, email, tokens):
    """Создать или обновить почтовый аккаунт"""
    account = MailAccount.query.filter_by(user_id=user_id, email=email).first()

    if not account:
        account = MailAccount(user_id=user_id, provider=provider, email=email)

    # Шифруем токены
    account.access_token = encrypt_token(tokens.get('access_token'))
    account.refresh_token = encrypt_token(tokens.get('refresh_token'))

    # Устанавливаем время истечения
    expires_in = tokens.get('expires_in', 3600)
    account.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    db.session.add(account)
    db.session.commit()

    return account