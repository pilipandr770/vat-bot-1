#!/usr/bin/env python3
"""Render critical templates with sample context and run schema validation.

This script creates a Flask app context (using `application.create_app()`),
renders selected templates into a temporary directory, then runs the
`validate_schema.py` validator against that directory (and public/).

Note: In CI the repository's `requirements.txt` should be installed first.
"""
import os
import sys
from pathlib import Path
import json

# Make project root importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from application import create_app
    from flask import render_template
except Exception as e:
    print("Error importing application. Ensure project dependencies are installed.")
    raise

from validate_schema import SchemaValidator


def make_sample_context():
    # Minimal objects used by templates
    current_user = type('U', (), {'is_authenticated': False, 'subscription_plan': None})()

    plans = [
        {
            'display_name': 'Free', 'price': 0.0, 'name': 'free', 'description': 'Kostenlos',
            'featured': False, 'api_calls': 5, 'period': 'Monat', 'features': ['VIES'], 'cta': 'Anmelden', 'cta_url': 'auth.register'
        },
        {
            'display_name': 'Starter', 'price': 29.0, 'name': 'starter', 'description': 'Starter Plan',
            'featured': True, 'api_calls': 50, 'period': 'Monat', 'features': ['VIES','OSINT'], 'cta': 'Starten', 'cta_url': 'payments.pricing'
        }
    ]

    page = {
        'title': 'Beispielseite',
        'url': '/vat-check/beispiel-berlin',
        'h1': 'VAT Check Berlin',
        'meta_description': 'Beispiel Meta',
        'meta_description_optimized': 'Optimierte Meta',
        'long_tail_keywords': ['vat prüfen berlin','ust idnr prüfen'],
        'schema': {"@type": "FAQPage", "mainEntity": []},
        'intro_text': 'Kurzbeschreibung',
        'cta_button': 'Prüfung starten',
        'faq': [],
        'case_study': None
    }

    return {'current_user': current_user, 'plans': plans, 'page': page}


def render_templates(app, out_dir: Path):
    ctx = make_sample_context()
    templates = [
        'landing.html',
        'payments/pricing.html',
        'programmatic/vat_check_page.html'
    ]

    out_dir.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        for tpl in templates:
            try:
                html = render_template(tpl, **ctx)
            except Exception as e:
                print(f"Failed to render {tpl}: {e}")
                raise
            target = out_dir / tpl.replace('/', '_')
            target.write_text(html, encoding='utf-8')
            print(f"Rendered {tpl} -> {target}")


def run_validation(rendered_dir: Path):
    validator = SchemaValidator()
    # validate public/ as usual
    if Path('public/').exists():
        validator.validate_directory(Path('public/'))
    # validate rendered templates
    validator.validate_directory(rendered_dir)


def main():
    app = create_app()
    out = ROOT / 'tmp_rendered'
    if out.exists():
        for f in out.iterdir():
            f.unlink()
    render_templates(app, out)
    run_validation(out)


if __name__ == '__main__':
    main()
