from app import create_app
from crm.models import db
from auth.models import User

app = create_app('development')

with app.app_context():
    # Test user registration
    test_user = User.query.filter_by(email='test@example.com').first()

    if test_user:
        print("⚠️  Test user already exists!")
        print(f"   Email: {test_user.email}")
        print(f"   Confirmed: {test_user.is_email_confirmed}")
        print(f"   Active: {test_user.is_active}")
    else:
        # Create test user
        test_user = User(
            email='test@example.com',
            first_name='Test',
            last_name='User',
            company_name='Test Company',
            country='DE',
            is_active=True,
            is_admin=False,
            is_email_confirmed=True  # Auto-confirmed for testing
        )
        test_user.set_password('test123')

        db.session.add(test_user)
        db.session.commit()

        print("✅ Test user created!")
        print(f"   Email: {test_user.email}")
        print(f"   Password: test123")
        print(f"   Confirmed: {test_user.is_email_confirmed}")
        print(f"   Can verify: {test_user.can_perform_verification()}")