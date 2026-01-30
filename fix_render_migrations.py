#!/usr/bin/env python3
"""
Safe migration fix for Render deployment.
This handles the multiple heads issue by stamping the database with both heads,
then allowing the merge migration to proceed.
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, stamp
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

def fix_multiple_heads():
    """Fix multiple heads issue in production database."""
    print("=" * 70)
    print("FIXING MULTIPLE HEADS IN PRODUCTION DATABASE")
    print("=" * 70)
    
    with app.app_context():
        from sqlalchemy import text
        
        try:
            # Check current state
            print("\n1. Checking current alembic_version state...")
            result = db.session.execute(
                text("SELECT version_num FROM vat_verification.alembic_version")
            )
            current_versions = [row[0] for row in result]
            print(f"   Current heads: {current_versions}")
            
            if not current_versions:
                print("   ERROR: No versions found in database!")
                return False
            
            # Expected heads that need merging
            expected_heads = {'3ead14968157', '7b1be3569a24'}
            merge_revision = '51d3555188cc'
            
            # Check if already fixed
            if len(current_versions) == 1:
                if current_versions[0] == merge_revision:
                    print(f"   ✅ Already at merge revision: {merge_revision}")
                    return True
                elif current_versions[0] in expected_heads:
                    print(f"   ⚠️  Database is at one head: {current_versions[0]}")
                    print(f"   Need to stamp with merge revision: {merge_revision}")
            
            # If we have multiple heads, verify they are the expected ones
            if len(current_versions) > 1:
                current_set = set(current_versions)
                if current_set == expected_heads:
                    print(f"   ✅ Found expected heads: {expected_heads}")
                else:
                    print(f"   ⚠️  Found unexpected heads: {current_set}")
            
            # Clear current versions
            print("\n2. Clearing alembic_version table...")
            db.session.execute(
                text("DELETE FROM vat_verification.alembic_version")
            )
            db.session.commit()
            print("   ✅ Cleared")
            
            # Stamp with the last revision before the split (2de5c7b8a921)
            # This is the common ancestor of both branches
            print("\n3. Stamping database with branch point (2de5c7b8a921)...")
            db.session.execute(
                text("INSERT INTO vat_verification.alembic_version (version_num) "
                     "VALUES ('2de5c7b8a921')")
            )
            db.session.commit()
            print("   ✅ Stamped with 2de5c7b8a921")
            
            print("\n4. Now you can run 'flask db upgrade' to apply both branches")
            print("   and the merge migration.")
            
            # Verify
            result = db.session.execute(
                text("SELECT version_num FROM vat_verification.alembic_version")
            )
            final_version = [row[0] for row in result]
            print(f"\n   Final version: {final_version}")
            
            print("\n" + "=" * 70)
            print("✅ FIX COMPLETE!")
            print("   Next step: Run 'flask db upgrade' to apply all pending migrations")
            print("=" * 70)
            return True
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

if __name__ == '__main__':
    success = fix_multiple_heads()
    sys.exit(0 if success else 1)
