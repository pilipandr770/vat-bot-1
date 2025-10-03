"""
Initialize database with all tables
"""
from app import create_app
from crm.models import db
from auth.models import User, Subscription, Payment

# Create Flask app
app = create_app()

with app.app_context():
    # Drop all tables (clean slate)
    db.drop_all()
    
    # Create all tables
    db.create_all()
    
    print("✅ Database initialized successfully!")
    print("📊 Created tables:")
    print("   - users")
    print("   - subscriptions")
    print("   - payments")
    print("   - companies")
    print("   - counterparties")
    print("   - verification_checks")
    print("   - check_results")
    print("\n🎯 Ready to create admin user!")
