"""Utility script to promote an existing user to admin status.

Usage:
    python promote_admin.py user@example.com [--password "NewPassword"] [--confirm-email]

This script is safe to run multiple times. It will:
  * set the `is_admin` flag to True
  * optionally update the password (if --password provided)
  * optionally mark the email as confirmed (if --confirm-email flag used)

Run inside the project virtualenv so the correct configuration and database are used.
"""

import argparse
import os
import sys

from application import create_app
from crm.models import db
from auth.models import User, Subscription


def promote_user(email: str, password: str | None, confirm_email: bool) -> int:
    """Promote a user by email. Returns exit status."""
    email_normalized = email.strip().lower()

    app = create_app(os.environ.get('FLASK_ENV', 'development'))

    with app.app_context():
        user = User.query.filter_by(email=email_normalized).first()
        if not user:
            print(f"❌ Benutzer mit E-Mail '{email_normalized}' wurde nicht gefunden.")
            return 1

        updated = False

        if not user.is_admin:
            user.is_admin = True
            updated = True
            print("✅ Flag 'is_admin' wurde gesetzt.")
        else:
            print("ℹ️  Benutzer ist bereits als Admin markiert.")

        if password:
            user.set_password(password)
            updated = True
            print("🔐 Passwort wurde aktualisiert.")

        if confirm_email and not user.is_email_confirmed:
            user.is_email_confirmed = True
            updated = True
            print("📧 E-Mail-Adresse wurde als bestätigt markiert.")

        if not user.is_active:
            user.is_active = True
            updated = True
            print("✅ Konto wurde aktiviert.")

        if updated:
            db.session.commit()
            print(f"🎉 Benutzer {email_normalized} ist jetzt Admin.")
        else:
            print("ℹ️  Keine Änderungen erforderlich.")

        # Ensure user has at least a free subscription for consistency
        if not user.subscriptions.filter(Subscription.status == 'active').first():
            free_subscription = Subscription(
                user_id=user.id,
                plan='free',
                status='active',
                api_calls_limit=5,
                api_calls_used=0
            )
            db.session.add(free_subscription)
            db.session.commit()
            print("➕ Kostenlose Subscription wurde hinzugefügt.")

    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Promote existing user to admin")
    parser.add_argument('email', help='E-Mail-Adresse des Benutzers')
    parser.add_argument('--password', help='Optional neues Passwort setzen')
    parser.add_argument('--confirm-email', action='store_true', help='E-Mail als bestätigt markieren')

    args = parser.parse_args(argv)
    return promote_user(args.email, args.password, args.confirm_email)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
