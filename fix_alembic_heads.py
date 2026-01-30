#!/usr/bin/env python3
"""
Script to fix multiple heads issue in Alembic migrations on Render.
This script should be run directly on Render using the shell command.

Usage:
  python fix_alembic_heads.py
"""
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment variables")
    exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

print("=" * 60)
print("ALEMBIC HEADS FIX SCRIPT")
print("=" * 60)

try:
    with engine.connect() as conn:
        # Check current state
        print("\n1. Checking current alembic_version state...")
        result = conn.execute(text("SELECT * FROM vat_verification.alembic_version"))
        current_versions = [row[0] for row in result]
        print(f"   Current versions in database: {current_versions}")
        
        if len(current_versions) == 0:
            print("   Database has no migrations applied!")
            exit(1)
        elif len(current_versions) == 1:
            print(f"   Database already has single head: {current_versions[0]}")
            if current_versions[0] == '51d3555188cc':
                print("   ✅ Already fixed! Nothing to do.")
                exit(0)
        
        # Delete all current versions
        print("\n2. Clearing current version entries...")
        conn.execute(text("DELETE FROM vat_verification.alembic_version"))
        conn.commit()
        print("   ✅ Cleared")
        
        # Find the latest common ancestor before the split
        # Based on the migration history, 2de5c7b8a921 is the branch point
        # We need to set the head to the merge point
        print("\n3. Setting head to merge migration (51d3555188cc)...")
        conn.execute(text(
            "INSERT INTO vat_verification.alembic_version (version_num) "
            "VALUES ('51d3555188cc')"
        ))
        conn.commit()
        print("   ✅ Set head to 51d3555188cc")
        
        # Verify
        print("\n4. Verifying fix...")
        result = conn.execute(text("SELECT * FROM vat_verification.alembic_version"))
        final_versions = [row[0] for row in result]
        print(f"   Final version in database: {final_versions}")
        
        if len(final_versions) == 1 and final_versions[0] == '51d3555188cc':
            print("\n" + "=" * 60)
            print("✅ SUCCESS! Alembic heads fixed.")
            print("   Database is now at merge point: 51d3555188cc")
            print("   You can now run 'flask db upgrade' safely.")
            print("=" * 60)
        else:
            print("\n❌ ERROR: Fix did not work as expected")
            exit(1)
            
except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
