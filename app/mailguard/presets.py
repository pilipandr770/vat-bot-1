"""
Email Provider Presets for Easy IMAP/SMTP Configuration
Спрощує підключення популярних email провайдерів
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
                <strong>⚠️ Не використовуйте звичайний пароль!</strong><br>
                Gmail потребує спеціальний <strong>App Password</strong> (пароль додатку).
            </div>
            <strong>Як отримати App Password:</strong>
            <ol class="small mb-2">
                <li>Увімкніть 2-Factor Authentication в Google</li>
                <li>Перейдіть за посиланням нижче</li>
                <li>Оберіть "Mail" та згенеруйте пароль</li>
                <li>Скопіюйте 16-символьний код (без пробілів)</li>
            </ol>
            <a href="https://myaccount.google.com/apppasswords" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Створити App Password в Google
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
                <strong>⚠️ Microsoft потребує App Password</strong><br>
                Не використовуйте звичайний пароль від облікового запису!
            </div>
            <strong>Як отримати App Password:</strong>
            <ol class="small mb-2">
                <li>Увімкніть 2-Factor Authentication в Microsoft Account</li>
                <li>Перейдіть: Security → Advanced security options</li>
                <li>Створіть App Password для пошти</li>
                <li>Використайте згенерований пароль</li>
            </ol>
            <a href="https://account.microsoft.com/security" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Налаштування безпеки Microsoft
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
                <strong>⚠️ Yahoo потребує App Password</strong><br>
                Звичайний пароль не працюватиме для IMAP/SMTP!
            </div>
            <strong>Як отримати App Password:</strong>
            <ol class="small mb-2">
                <li>Перейдіть за посиланням нижче</li>
                <li>Виберіть "Other App" та введіть "Mail Client"</li>
                <li>Натисніть "Generate" та скопіюйте пароль</li>
                <li>Використайте цей пароль в формі підключення</li>
            </ol>
            <a href="https://login.yahoo.com/account/security/app-passwords" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Створити App Password в Yahoo
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
                <strong>⚠️ Mail.ru потребує пароль додатку</strong><br>
                Звичайний пароль не підходить для підключення!
            </div>
            <strong>Як отримати пароль додатку:</strong>
            <ol class="small mb-2">
                <li>Перейдіть в Налаштування → Пароль і безпека</li>
                <li>Знайдіть "Паролі для зовнішніх додатків"</li>
                <li>Натисніть "Згенерувати новий пароль"</li>
                <li>Скопіюйте згенерований пароль</li>
            </ol>
            <a href="https://account.mail.ru/user/2-step-auth/passwords/" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Налаштування паролів Mail.ru
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
                <strong>⚠️ Yandex потребує пароль додатку</strong><br>
                Основний пароль не працює для IMAP/SMTP!
            </div>
            <strong>Як отримати пароль додатку:</strong>
            <ol class="small mb-2">
                <li>Перейдіть за посиланням нижче</li>
                <li>Натисніть "Створити пароль додатку"</li>
                <li>Введіть назву (наприклад, "MailGuard")</li>
                <li>Скопіюйте згенерований пароль</li>
            </ol>
            <a href="https://id.yandex.ru/security/app-passwords" target="_blank" class="btn btn-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Створити пароль додатку Yandex
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
                <strong>✅ UKR.NET підтримує звичайний пароль</strong><br>
                Використовуйте той самий пароль, яким входите в поштову скриньку.
            </div>
            <strong>Налаштування:</strong>
            <ul class="small mb-2">
                <li>Email: ваша адреса @ukr.net</li>
                <li>Пароль: звичайний пароль від пошти</li>
                <li>Не потрібні додаткові App Passwords</li>
            </ul>
            <a href="https://www.ukr.net/" target="_blank" class="btn btn-outline-primary btn-sm">
                <i class="bi bi-box-arrow-up-right"></i> Відкрити UKR.NET
            </a>
        '''
    },
    'custom': {
        'name': 'Інший провайдер (Custom)',
        'imap_host': '',
        'imap_port': 993,
        'imap_ssl': True,
        'smtp_host': '',
        'smtp_port': 587,
        'smtp_ssl': False,
        'smtp_tls': True,
        'instructions': '''
            <div class="alert alert-info mb-2">
                <strong>ℹ️ Налаштування вручну</strong><br>
                Заповніть всі поля IMAP та SMTP самостійно.
            </div>
            <strong>Де знайти налаштування:</strong>
            <ul class="small mb-2">
                <li>Перевірте документацію вашого email провайдера</li>
                <li>Зазвичай: imap.yourdomain.com / smtp.yourdomain.com</li>
                <li>Порти: IMAP 993 (SSL) або 143, SMTP 587 (TLS) або 465 (SSL)</li>
                <li>Деякі провайдери потребують App Password</li>
            </ul>
            <p class="small text-muted">
                Популярні домени: FastMail, ProtonMail, Zoho, власні корпоративні сервери.
            </p>
        '''
    }
}


def get_preset(provider_key):
    """Отримати preset для провайдера"""
    return EMAIL_PRESETS.get(provider_key, EMAIL_PRESETS['custom'])


def get_all_presets():
    """Отримати список всіх доступних провайдерів"""
    return [
        {'key': key, 'name': preset['name']}
        for key, preset in EMAIL_PRESETS.items()
    ]
