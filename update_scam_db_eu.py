#!/usr/bin/env python3
"""
Script to update European scam phone number databases from community repositories.
Run this periodically to keep the scam databases current.
"""

import os
import requests
from datetime import datetime
import re

def update_french_scam_database():
    """Download and merge French scam databases from multiple sources."""
    local_path = os.path.join(os.path.dirname(__file__), 'spam_database_fr.txt')
    french_numbers = set()

    print("🔄 Updating French scam database...")

    # Source 1: gitbra/spam repository (phone_numbers.txt)
    try:
        url1 = "https://raw.githubusercontent.com/gitbra/spam/main/phone_numbers.txt"
        response1 = requests.get(url1, timeout=30)
        response1.raise_for_status()

        lines = response1.text.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and '?' in line:
                # Convert pattern like "012345?" to French format
                # These are French numbers without country code
                base_number = line.replace('?', '')
                if len(base_number) >= 9:  # Valid French number length
                    # Add as +33 prefix
                    french_number = f"+33{base_number}"
                    french_numbers.add(french_number)

        print(f"✅ Loaded {len(french_numbers)} numbers from gitbra/spam")

    except Exception as e:
        print(f"❌ Failed to load gitbra/spam: {e}")

    # Source 2: Esdayl/NoPhoneSpam_FR repository (NoPhoneSpam_blacklist.txt)
    try:
        url2 = "https://raw.githubusercontent.com/Esdayl/NoPhoneSpam_FR/main/NoPhoneSpam_blacklist.txt"
        response2 = requests.get(url2, timeout=30)
        response2.raise_for_status()

        lines = response2.text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('+33') and '%' in line:
                # Extract prefix patterns like "+33162%: Démarchage 0162"
                prefix = line.split('%')[0]  # e.g., "+33162"
                if len(prefix) > 3:  # Valid prefix
                    # Add the base prefix (will be used for pattern matching)
                    french_numbers.add(prefix + "?")  # Add ? for pattern matching

        print(f"✅ Added prefix patterns from NoPhoneSpam_FR")

    except Exception as e:
        print(f"❌ Failed to load NoPhoneSpam_FR: {e}")

    # Source 3: alexdyas/spamnumbers-france (if available)
    try:
        # Try to get the raw content - this might be a single file or multiple files
        url3 = "https://raw.githubusercontent.com/alexdyas/spamnumbers-france/main/spam-numbers.txt"
        response3 = requests.get(url3, timeout=30)
        if response3.status_code == 200:
            lines = response3.text.split('\n')
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit():
                    # Convert local French numbers to E164
                    if len(line) == 10 and line.startswith('0'):
                        # Convert 0123456789 to +33123456789
                        french_number = f"+33{line[1:]}"
                        french_numbers.add(french_number)

            print(f"✅ Added numbers from alexdyas/spamnumbers-france")

    except Exception as e:
        print(f"⚠️  alexdyas/spamnumbers-france not available or different format: {e}")

    # Save merged database
    try:
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write("# French Scam Phone Numbers Database\n")
            f.write(f"# Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# Sources: gitbra/spam, Esdayl/NoPhoneSpam_FR, alexdyas/spamnumbers-france\n")
            f.write("# Format: E164 (+33123456789) or patterns (+33162?)\n\n")

            for number in sorted(french_numbers):
                f.write(f"{number}\n")

        print(f"✅ Successfully updated French scam database: {len(french_numbers)} entries")
        print(f"📁 Saved to: {local_path}")

        return True

    except Exception as e:
        print(f"❌ Failed to save French database: {e}")
        return False

def update_scam_databases():
    """Update all European scam databases."""
    print("🌍 Updating European scam phone databases...\n")

    success_count = 0

    # Update French database
    if update_french_scam_database():
        success_count += 1

    # Add more countries here as needed
    # if update_german_scam_database():
    #     success_count += 1

    print(f"\n✅ Updated {success_count} European databases")
    return success_count > 0

if __name__ == "__main__":
    update_scam_databases()