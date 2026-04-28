"""
Create first admin user with a randomly generated password.
Run once on a fresh deployment; the password is printed once and never stored in code.
"""
import secrets
import string
from application import create_app
from crm.models import db
from auth.models import User, Subscription
from datetime import datetime, timedelta


def _generate_password(length: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


app = create_app()

with app.app_context():
    admin = User.query.filter_by(email='admin@example.com').first()

    if admin:
        print("⚠️  Admin user already exists!")
        print(f"   Email: {admin.email}")
        print(f"   Admin: {admin.is_admin}")
    else:
        password = _generate_password()

        admin = User(
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            company_name='VAT Verification Admin',
            country='DE',
            is_active=True,
            is_admin=True,
            is_email_confirmed=True,
            created_at=datetime.utcnow()
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.flush()

        subscription = Subscription(
            user_id=admin.id,
            plan='free',
            status='active',
            api_calls_limit=5,
            api_calls_used=0,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=365),
            monthly_price=0.0
        )

        db.session.add(subscription)
        db.session.commit()

        print("✅ Admin user created successfully!")
        print(f"   Email: admin@example.com")
        print(f"   Password: {password}")
        print("\n⚠️  Save this password now — it will not be shown again!")
        print("🚀 Login at: http://127.0.0.1:5000/auth/login")
