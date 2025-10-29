"""
Migration script to fix user_id for existing counterparties and companies.
Run this once to populate user_id from verification_checks.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from application import create_app
from crm.models import db, Company, Counterparty, VerificationCheck

def migrate_user_ids():
    """Populate user_id for counterparties and companies from their verification checks."""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("MIGRATION: Populating user_id for CRM records")
        print("=" * 60)
        
        # Fix counterparties
        counterparties_fixed = 0
        counterparties_without_checks = []
        
        counterparties = Counterparty.query.filter_by(user_id=None).all()
        print(f"\nFound {len(counterparties)} counterparties without user_id")
        
        for cp in counterparties:
            # Find first verification check for this counterparty
            check = VerificationCheck.query.filter_by(counterparty_id=cp.id).first()
            if check and check.user_id:
                cp.user_id = check.user_id
                counterparties_fixed += 1
                print(f"✓ Counterparty '{cp.company_name}' → user_id={check.user_id}")
            else:
                counterparties_without_checks.append(cp)
                print(f"⚠ Counterparty '{cp.company_name}' has no verification checks!")
        
        # Fix companies
        companies_fixed = 0
        companies_without_checks = []
        
        companies = Company.query.filter_by(user_id=None).all()
        print(f"\nFound {len(companies)} companies without user_id")
        
        for company in companies:
            # Find first verification check for this company
            check = VerificationCheck.query.filter_by(company_id=company.id).first()
            if check and check.user_id:
                company.user_id = check.user_id
                companies_fixed += 1
                print(f"✓ Company '{company.company_name}' → user_id={check.user_id}")
            else:
                companies_without_checks.append(company)
                print(f"⚠ Company '{company.company_name}' has no verification checks!")
        
        # Commit changes
        db.session.commit()
        
        # Summary
        print("\n" + "=" * 60)
        print("MIGRATION COMPLETE")
        print("=" * 60)
        print(f"✅ Counterparties fixed: {counterparties_fixed}")
        print(f"✅ Companies fixed: {companies_fixed}")
        
        if counterparties_without_checks:
            print(f"\n⚠️  Counterparties without checks (orphaned): {len(counterparties_without_checks)}")
            print("   These will remain without user_id. Consider deleting them:")
            for cp in counterparties_without_checks:
                print(f"   - ID {cp.id}: {cp.company_name} ({cp.country})")
        
        if companies_without_checks:
            print(f"\n⚠️  Companies without checks (orphaned): {len(companies_without_checks)}")
            print("   These will remain without user_id. Consider deleting them:")
            for c in companies_without_checks:
                print(f"   - ID {c.id}: {c.company_name}")
        
        print("\n✨ Migration successful! Now restart your Flask server.\n")

if __name__ == '__main__':
    migrate_user_ids()
