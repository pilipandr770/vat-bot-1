"""
Create first admin user
"""
from application import create_app
from crm.models import db
from auth.models import User, Subscription
from datetime import datetime, timedelta

# Create Flask app
app = create_app()

with app.app_context():
    # Check if admin already exists
    admin = User.query.filter_by(email='admin@example.com').first()
    
    if admin:
        print("⚠️  Admin user already exists!")
        print(f"   Email: {admin.email}")
        print(f"   Admin: {admin.is_admin}")
    else:
        # Create admin user
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
        admin.set_password('admin123')  # Change this in production!
        
        db.session.add(admin)
        db.session.flush()  # Get admin ID
        
        # Create free subscription for admin
        subscription = Subscription(
            user_id=admin.id,
            plan='free',
            status='active',
            api_calls_limit=5,
            api_calls_used=0,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=365),  # 1 year
            monthly_price=0.0
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        print("✅ Admin user created successfully!")
        print(f"   Email: admin@example.com")
        print(f"   Password: admin123")
        print(f"   Plan: Free (5 checks/month)")
        print("\n⚠️  Remember to change the password after first login!")
        print("\n🚀 You can now login at: http://127.0.0.1:5000/auth/login")
