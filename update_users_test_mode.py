"""
Update existing users to have email_confirmed = True for testing mode.
Run this script once to update all existing users.
"""

import os
from app import create_app
from auth.models import User
from crm.models import db

def update_existing_users():
    """Set is_email_confirmed=True for all existing users."""
    app = create_app()
    
    with app.app_context():
        try:
            # Get all users where email is not confirmed
            unconfirmed_users = User.query.filter_by(is_email_confirmed=False).all()
            
            if not unconfirmed_users:
                print("✅ All users already have confirmed emails!")
                return
            
            print(f"\n🔄 Found {len(unconfirmed_users)} users without email confirmation")
            print("Updating to TEST MODE (email confirmed = True)...\n")
            
            for user in unconfirmed_users:
                user.is_email_confirmed = True
                print(f"   ✓ Updated: {user.email}")
            
            db.session.commit()
            print(f"\n✅ Successfully updated {len(unconfirmed_users)} users!")
            print("All users can now login without email confirmation.\n")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error updating users: {str(e)}\n")
            raise

if __name__ == '__main__':
    print("=" * 60)
    print("UPDATE USERS FOR TEST MODE - Email Confirmation Disabled")
    print("=" * 60)
    update_existing_users()
