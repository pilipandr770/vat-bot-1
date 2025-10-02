"""
Test script to verify basic functionality of the Counterparty Verification System.
Run this to test API services and database operations.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from crm.models import db, Company, Counterparty, VerificationCheck
from services.vies import VIESService
from services.sanctions import SanctionsService
from services.handelsregister import HandelsregisterService

def test_database_connection():
    """Test database connection and tables."""
    print("\n🔍 Testing database connection...")
    try:
        app = create_app()
        with app.app_context():
            # Test table access
            company_count = Company.query.count()
            counterparty_count = Counterparty.query.count()
            check_count = VerificationCheck.query.count()
            
            print(f"✅ Database connected successfully")
            print(f"   - Companies: {company_count}")
            print(f"   - Counterparties: {counterparty_count}")
            print(f"   - Verification checks: {check_count}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_vies_service():
    """Test VIES VAT validation service."""
    print("\n🔍 Testing VIES service...")
    try:
        vies = VIESService()
        
        # Test with a mock VAT number
        result = vies.validate_vat('DE', '123456789')
        
        print(f"✅ VIES service working")
        print(f"   - Status: {result.get('status')}")
        print(f"   - Confidence: {result.get('confidence')}")
        print(f"   - Response time: {result.get('response_time_ms')}ms")
        
        # Test VAT format validation
        format_check = vies.validate_vat_format('DE', 'DE123456789')
        print(f"   - Format validation: {'Valid' if format_check['valid'] else 'Invalid'}")
        
        return True
    except Exception as e:
        print(f"❌ VIES service failed: {e}")
        return False

def test_sanctions_service():
    """Test sanctions list checking service."""
    print("\n🔍 Testing Sanctions service...")
    try:
        sanctions = SanctionsService()
        
        # Test with a safe company name
        result = sanctions.check_sanctions('Test Company GmbH', '')
        
        print(f"✅ Sanctions service working")
        print(f"   - Status: {result.get('status')}")
        print(f"   - Sanctions found: {result.get('data', {}).get('total_matches', 0)}")
        print(f"   - Sources checked: {len(result.get('data', {}).get('checked_sources', []))}")
        
        # Test source availability
        sources_status = sanctions.get_sanctions_sources_status()
        print(f"   - Available sources: {sources_status.get('total_available', 0)}")
        
        return True
    except Exception as e:
        print(f"❌ Sanctions service failed: {e}")
        return False

def test_handelsregister_service():
    """Test Handelsregister service."""
    print("\n🔍 Testing Handelsregister service...")
    try:
        handelsregister = HandelsregisterService()
        
        # Test with a mock company name
        result = handelsregister.check_company('BMW AG')
        
        print(f"✅ Handelsregister service working")
        print(f"   - Status: {result.get('status')}")
        print(f"   - Confidence: {result.get('confidence')}")
        print(f"   - Matches: {result.get('data', {}).get('total_matches', 0)}")
        
        # Test service availability
        availability = handelsregister.check_service_availability()
        print(f"   - Service available: {'Yes' if availability.get('available') else 'No'}")
        
        return True
    except Exception as e:
        print(f"❌ Handelsregister service failed: {e}")
        return False

def test_create_sample_data():
    """Create sample verification for testing."""
    print("\n🔍 Creating sample verification data...")
    try:
        app = create_app()
        with app.app_context():
            # Create sample company
            company = Company(
                vat_number='DE123456789',
                company_name='Test Company GmbH',
                legal_address='Test Street 1, 10115 Berlin, Germany',
                email='test@example.com',
                phone='+49 30 12345678'
            )
            db.session.add(company)
            
            # Create sample counterparty
            counterparty = Counterparty(
                vat_number='DE987654321',
                company_name='Sample Counterparty AG',
                address='Sample Street 10, 80331 München, Germany',
                email='contact@sample.com',
                domain='sample.com',
                country='DE'
            )
            db.session.add(counterparty)
            
            db.session.commit()
            
            print(f"✅ Sample data created")
            print(f"   - Company ID: {company.id}")
            print(f"   - Counterparty ID: {counterparty.id}")
            
            return True
    except Exception as e:
        print(f"❌ Sample data creation failed: {e}")
        return False

def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Counterparty Verification System - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("VIES Service", test_vies_service),
        ("Sanctions Service", test_sanctions_service),
        ("Handelsregister Service", test_handelsregister_service),
        ("Sample Data Creation", test_create_sample_data)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)