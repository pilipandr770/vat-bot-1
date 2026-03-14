#!/usr/bin/env python3
"""
Script to update the scam phone number database from BlockGuard repository.
Run this periodically to keep the scam database current.
"""

import os
import requests
from datetime import datetime

def update_scam_database():
    """Download the latest scam database from BlockGuard GitHub repository."""
    url = "https://raw.githubusercontent.com/Derek-G1/block-guard-data/main/spam_database.txt"
    local_path = os.path.join(os.path.dirname(__file__), 'spam_database.txt')

    print(f"Downloading scam database from {url}...")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(response.text)

        # Count lines
        with open(local_path, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f if line.strip())

        print(f"✅ Successfully updated scam database: {line_count} numbers")
        print(f"📁 Saved to: {local_path}")
        print(f"🕒 Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return True

    except Exception as e:
        print(f"❌ Failed to update scam database: {e}")
        return False

if __name__ == "__main__":
    update_scam_database()