#!/usr/bin/env python3
"""Generate a secure SECRET_KEY for Flask application."""
import secrets

if __name__ == '__main__':
    secret_key = secrets.token_urlsafe(32)
    print("=" * 60)
    print("🔐 Generated SECRET_KEY for Flask:")
    print("=" * 60)
    print(secret_key)
    print("=" * 60)
    print("\n💡 Add this to your Render.com Environment Variables:")
    print(f"SECRET_KEY={secret_key}")
    print("\n⚠️  Keep this secret and never commit it to git!")
