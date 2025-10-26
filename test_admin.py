from app import create_app
from crm.models import db
from auth.models import User

app = create_app('development')

with app.app_context():
    # Check admin user
    admin = User.query.filter_by(email='admin@example.com').first()

    if admin:
        print("🔧 Admin User Status:")
        print(f"   Email: {admin.email}")
        print(f"   Admin: {admin.is_admin}")
        print(f"   Confirmed: {admin.is_email_confirmed}")
        print(f"   Can verify: {admin.can_perform_verification()}")

        # Check subscription
        sub = admin.active_subscription
        if sub:
            print(f"   Plan: {sub.plan}")
            print(f"   Status: {sub.status}")
            print(f"   API Limit: {sub.api_calls_limit}")
            print(f"   API Used: {sub.api_calls_used}")
        else:
            print("   No active subscription")
    else:
        print("❌ Admin user not found!")