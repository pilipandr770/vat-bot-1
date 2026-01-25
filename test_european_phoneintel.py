#!/usr/bin/env python3
"""
Test script for European phone intelligence with scam databases.
"""

from app.services.phoneintel import get_service

def test_european_numbers():
    """Test phone analysis with European numbers."""

    service = get_service()

    # Test French numbers
    french_numbers = [
        "+33123456789",  # Regular French number
        "+33162234567",  # Should match +33162? pattern
        "+33163345678",  # Should match +33163? pattern
        "+33947612345",  # Should match +339476? pattern
        "+33123456789",  # Should NOT match any pattern
    ]

    print("🧪 Testing European Phone Intelligence Service")
    print("=" * 50)

    for number in french_numbers:
        result = service.analyze(number)
        print(f"\n📞 Number: {number}")
        print(f"   Country: {result['country']}")
        print(f"   Carrier: {result['carrier']}")
        print(f"   Line Type: {result['line_type']}")
        print(f"   Seen in Scam DB: {result['seen_in_scam_db']}")
        print(f"   Suspicious Patterns: {result['suspicious_patterns']}")
        print(f"   Risk Score: {result['risk_score']}")
        print(f"   Verdict: {result['verdict']}")

    # Test US number (should still work)
    us_number = "+12015551234"
    result = service.analyze(us_number)
    print(f"\n📞 US Number: {us_number}")
    print(f"   Country: {result['country']}")
    print(f"   Seen in Scam DB: {result['seen_in_scam_db']}")
    print(f"   Risk Score: {result['risk_score']}")
    print(f"   Verdict: {result['verdict']}")

if __name__ == "__main__":
    test_european_numbers()