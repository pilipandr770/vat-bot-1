"""
Email Provider Presets for Easy IMAP/SMTP Configuration
Vereinfacht die Verbindung beliebter E-Mail-Anbieter
"""

EMAIL_PRESETS = {
    'gmail': {
        'name': 'Gmail',
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_ssl': True,
        'smtp_tls': True,
        'instructions': '''
            <div class="alert alert-warning mb-2">
                <strong>⚠️ Verwenden Sie nicht Ihr normales Passwort!</strong><br>
                Gmail benötigt ein spezielles <strong>App-Passwort</strong>.
            </div>
            <strong>So erhalten Sie ein App-Passwort:</strong>
            <ol class="small mb-2">
                <li>Aktivieren Sie die 2-Faktor-Authentifizierung bei Google</li>
                <li>Klicken Sie auf den Link unten</li>
                <li>Wählen Sie "Mail" und generieren Sie ein Passwort</li>
                <li>Kopieren Sie den 16-stelligen Code (ohne Leerzeichen)</li>
            </ol>
            <a href="https://myaccount.google.com/apppasswords" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> App-Passwort in Google erstellen
            </a>
        '''
    },
    'outlook': {
        'name': 'Outlook / Hotmail / Live',
        'imap_host': 'outlook.office365.com',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': 'smtp-mail.outlook.com',
        'smtp_port': 587,
        'smtp_ssl': False,
        'smtp_tls': True,
        'instructions': '''
            <div class="alert alert-warning mb-2">
                <strong>⚠️ Microsoft benötigt ein App-Passwort</strong><br>
                Verwenden Sie nicht Ihr normales Konto-Passwort!
            </div>
            <strong>So erhalten Sie ein App-Passwort:</strong>
            <ol class="small mb-2">
                <li>Aktivieren Sie die 2-Faktor-Authentifizierung im Microsoft-Konto</li>
                <li>Gehen Sie zu: Sicherheit → Erweiterte Sicherheitsoptionen</li>
                <li>Erstellen Sie ein App-Passwort für E-Mail</li>
                <li>Verwenden Sie das generierte Passwort</li>
            </ol>
            <a href="https://account.microsoft.com/security" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Microsoft-Sicherheitseinstellungen
            </a>
        '''
    },
    'yahoo': {
        'name': 'Yahoo Mail',
        'imap_host': 'imap.mail.yahoo.com',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': 'smtp.mail.yahoo.com',
        'smtp_port': 587,
        'smtp_ssl': False,
        'smtp_tls': True,
        'instructions': '''
            <div class="alert alert-warning mb-2">
                <strong>⚠️ Yahoo benötigt ein App-Passwort</strong><br>
                Das normale Passwort funktioniert nicht für IMAP/SMTP!
            </div>
            <strong>So erhalten Sie ein App-Passwort:</strong>
            <ol class="small mb-2">
                <li>Klicken Sie auf den Link unten</li>
                <li>Wählen Sie "Other App" und geben Sie "Mail Client" ein</li>
                <li>Klicken Sie auf "Generate" und kopieren Sie das Passwort</li>
                <li>Verwenden Sie dieses Passwort im Verbindungsformular</li>
            </ol>
            <a href="https://login.yahoo.com/account/security/app-passwords" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> App-Passwort in Yahoo erstellen
            </a>
        '''
    },
    'mailru': {
        'name': 'Mail.ru',
        'imap_host': 'imap.mail.ru',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': 'smtp.mail.ru',
        'smtp_port': 465,
        'smtp_ssl': True,
        'smtp_tls': False,
        'instructions': '''
            <div class="alert alert-warning mb-2">
                <strong>⚠️ Mail.ru benötigt ein App-Passwort</strong><br>
                Das normale Passwort ist für die Verbindung nicht geeignet!
            </div>
            <strong>So erhalten Sie ein App-Passwort:</strong>
            <ol class="small mb-2">
                <li>Gehen Sie zu Einstellungen → Passwort und Sicherheit</li>
                <li>Suchen Sie "Passwörter für externe Anwendungen"</li>
                <li>Klicken Sie auf "Neues Passwort generieren"</li>
                <li>Kopieren Sie das generierte Passwort</li>
            </ol>
            <a href="https://account.mail.ru/user/2-step-auth/passwords/" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Mail.ru Passwort-Einstellungen
            </a>
        '''
    },
    'yandex': {
        'name': 'Yandex Mail',
        'imap_host': 'imap.yandex.ru',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': 'smtp.yandex.ru',
        'smtp_port': 465,
        'smtp_ssl': True,
        'smtp_tls': False,
        'instructions': '''
            <div class="alert alert-warning mb-2">
                <strong>⚠️ Yandex benötigt ein App-Passwort</strong><br>
                Das Hauptpasswort funktioniert nicht für IMAP/SMTP!
            </div>
            <strong>So erhalten Sie ein App-Passwort:</strong>
            <ol class="small mb-2">
                <li>Klicken Sie auf den Link unten</li>
                <li>Klicken Sie auf "App-Passwort erstellen"</li>
                <li>Geben Sie einen Namen ein (z.B. "MailGuard")</li>
                <li>Kopieren Sie das generierte Passwort</li>
            </ol>
            <a href="https://id.yandex.ru/security/app-passwords" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Yandex App-Passwort erstellen
            </a>
        '''
    },
    'ukrnet': {
        'name': 'UKR.NET',
        'imap_host': 'imap.ukr.net',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': 'smtp.ukr.net',
        'smtp_port': 465,
        'smtp_ssl': True,
        'smtp_tls': False,
        'instructions': '''
            <div class="alert alert-success mb-2">
                <strong>✅ UKR.NET unterstützt normale Passwörter</strong><br>
                Verwenden Sie dasselbe Passwort, mit dem Sie sich in Ihr Postfach einloggen.
            </div>
            <strong>Einstellungen:</strong>
            <ul class="small mb-2">
                <li>E-Mail: Ihre Adresse @ukr.net</li>
                <li>Passwort: Ihr normales E-Mail-Passwort</li>
                <li>Keine zusätzlichen App-Passwörter erforderlich</li>
            </ul>
            <a href="https://www.ukr.net/" target="_blank" class="btn btn-outline-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> UKR.NET öffnen
            </a>
        '''
    },
    'custom': {
        'name': 'Anderer Anbieter (Custom)',
        'imap_host': '',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': '',
        'smtp_port': 587,
        'smtp_ssl': False,
        'smtp_tls': True,
        'instructions': '''
            <div class="alert alert-info mb-2">
                <strong>ℹ️ Manuelle Konfiguration</strong><br>
                Füllen Sie alle IMAP- und SMTP-Felder manuell aus.
            </div>
            <strong>Wo Sie die Einstellungen finden:</strong>
            <ul class="small mb-2">
                <li>Prüfen Sie die Dokumentation Ihres E-Mail-Anbieters</li>
                <li>Normalerweise: imap.ihredomain.com / smtp.ihredomain.com</li>
                <li>Ports: IMAP 993 (SSL) oder 143, SMTP 587 (TLS) oder 465 (SSL)</li>
                <li>Einige Anbieter benötigen App-Passwörter</li>
            </ul>
            <p class="small text-muted">
                Beliebte Domains: FastMail, ProtonMail, Zoho, eigene Unternehmensserver.
            </p>
        '''
    }
}


def get_preset(provider_key):
    """Preset für Anbieter abrufen"""
    return EMAIL_PRESETS.get(provider_key, EMAIL_PRESETS['custom'])


def get_all_presets():
    """Liste aller verfügbaren Anbieter abrufen"""
    return [
        {'key': key, 'name': preset['name']}
        for key, preset in EMAIL_PRESETS.items()
    ]
