"""
Test script to verify CRM counterparty saving after verification.
This script simulates a verification and checks if the counterparty appears in CRM.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_crm_integration():
    """Test that counterparties are saved to CRM after verification."""
    
    print("=" * 70)
    print("TEST: CRM Integration - Counterparty Auto-Save After Verification")
    print("=" * 70)
    
    # Step 1: Login
    print("\n[1/5] Logging in...")
    session = requests.Session()
    
    login_data = {
        'email': 'admin@example.com',  # Change to your test user
        'password': 'admin123'
    }
    
    response = session.post(f"{BASE_URL}/auth/login", data=login_data, allow_redirects=False)
    
    if response.status_code not in [200, 302]:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    print("✅ Login successful")
    
    # Step 2: Check CRM before verification
    print("\n[2/5] Checking CRM before verification...")
    response = session.get(f"{BASE_URL}/crm/api/counterparties")
    
    if response.status_code != 200:
        print(f"❌ CRM API error: {response.status_code}")
        return False
    
    before_count = len(response.json().get('counterparties', []))
    print(f"✅ Current counterparties in CRM: {before_count}")
    
    # Step 3: Run verification
    print("\n[3/5] Running verification for test counterparty...")
    
    verification_data = {
        'requester_vat': 'DE123456789',
        'requester_name': 'Test Company GmbH',
        'requester_address': 'Teststraße 1, 12345 Berlin',
        'requester_email': 'test@company.de',
        'requester_phone': '+49 30 12345678',
        'target_vat': 'DE260518613',  # Valid German VAT
        'target_name': 'Test Kontrahent GmbH',
        'target_address': 'Beispielweg 10, 10115 Berlin',
        'target_country': 'DE',
        'target_email': 'kontakt@kontrahent.de',
        'target_domain': 'kontrahent.de'
    }
    
    response = session.post(
        f"{BASE_URL}/verify",
        json=verification_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code != 200:
        print(f"❌ Verification failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    result = response.json()
    if not result.get('success'):
        print(f"❌ Verification error: {result.get('error')}")
        return False
    
    check_id = result.get('check_id')
    print(f"✅ Verification completed (Check ID: {check_id})")
    
    # Step 4: Check CRM after verification
    print("\n[4/5] Checking CRM after verification...")
    response = session.get(f"{BASE_URL}/crm/api/counterparties")
    
    if response.status_code != 200:
        print(f"❌ CRM API error: {response.status_code}")
        return False
    
    after_data = response.json()
    after_count = len(after_data.get('counterparties', []))
    print(f"✅ Counterparties in CRM after verification: {after_count}")
    
    # Step 5: Verify the new counterparty is in CRM
    print("\n[5/5] Verifying new counterparty in CRM...")
    
    found = False
    for cp in after_data.get('counterparties', []):
        if cp.get('vat_number') == verification_data['target_vat']:
            found = True
            print(f"✅ Found in CRM!")
            print(f"   - ID: {cp.get('id')}")
            print(f"   - Name: {cp.get('company_name')}")
            print(f"   - VAT: {cp.get('vat_number')}")
            print(f"   - Country: {cp.get('country')}")
            print(f"   - User ID: {cp.get('user_id')}")
            break
    
    if not found:
        print(f"❌ Counterparty NOT found in CRM!")
        print(f"   Expected VAT: {verification_data['target_vat']}")
        print(f"   Available counterparties:")
        for cp in after_data.get('counterparties', []):
            print(f"   - {cp.get('company_name')} ({cp.get('vat_number')})")
        return False
    
    # Final summary
    print("\n" + "=" * 70)
    print("TEST RESULT: ✅ SUCCESS")
    print("=" * 70)
    print(f"Counterparties before: {before_count}")
    print(f"Counterparties after: {after_count}")
    print(f"New counterparties: {after_count - before_count}")
    print("\n✨ CRM integration is working correctly!")
    print("   Verified counterparties are automatically saved to CRM with user_id")
    
    return True

if __name__ == '__main__':
    try:
        success = test_crm_integration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
