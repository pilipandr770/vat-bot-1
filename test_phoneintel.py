#!/usr/bin/env python3

from app.services.phoneintel import get_service

def test_scam_detection():
    service = get_service()

    # Test with a known scam number from the database
    scam_number = "+16502530000"  # This should be in the BlockGuard database
    result = service.analyze(scam_number, "US")

    print(f"Testing scam number: {scam_number}")
    print(f"Result: {result}")
    print(f"Scam database size: {len(service.scam_numbers)} numbers")

    # Test with a clean number
    clean_number = "+15551234567"  # Random US number, likely not in scam DB
    result2 = service.analyze(clean_number, "US")

    print(f"\nTesting clean number: {clean_number}")
    print(f"Result: {result2}")

    # Test with a real US number format
    real_us_number = "+12025550123"  # Area code 202 (Washington DC)
    result3 = service.analyze(real_us_number, "US")

    print(f"\nTesting real US number: {real_us_number}")
    print(f"Result: {result3}")

if __name__ == "__main__":
    test_scam_detection()