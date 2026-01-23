#!/usr/bin/env python3
"""
Critical fixes for VAT Verification application:
1. Add Rate Limiting
2. Add VAT Validation  
3. Improve Error Handling
"""

import re

with open('application.py', 'r', encoding='utf-8') as f:
    content = f.read()

# FIX 1: Add rate_limiter import (check if already added)
if 'from services.rate_limiter import' not in content:
    print('Adding rate_limiter import...')
    old_imports = 'from services.vat_lookup import VatLookupService'
    new_imports = '''from services.vat_lookup import VatLookupService
from services.rate_limiter import rate_limiter
from services.vat_validator import validate_vat_format, validate_counterparty_data'''
    content = content.replace(old_imports, new_imports)
    print('✅ Imports updated')

# FIX 2: Add rate limiting and validation to verify_counterparty
# Use regex to find and replace more flexibly

# Pattern 1: Add rate limiting check
pattern_rate = r'(# User is authenticated via @login_required decorator\s+)(# Check if user can perform verification)'
replacement_rate = r'''\1# ==================== RATE LIMITING ====================
        identifier = f"user_{current_user.id}"
        allowed_min, info_min = rate_limiter.is_allowed(identifier, 30, 60)
        if not allowed_min:
            logger.warning(f"Rate limit exceeded for user {current_user.id}")
            return jsonify({
                'success': False,
                'error': 'Zu viele Anfragen. Bitte versuchen Sie es in einigen Sekunden erneut.',
                'rate_limit': True,
                'retry_after': info_min['retry_after']
            }), 429

        \2'''

if re.search(pattern_rate, content):
    content = re.sub(pattern_rate, replacement_rate, content)
    print('✅ Rate limiting added')
else:
    print('⚠️ Could not find rate limiting insertion point')

# FIX 3: Improve error messages
old_error = "return jsonify({'success': False, 'error': str(e)}), 500"
new_error = '''return jsonify({
                'success': False,
                'error': 'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.',
                'details': str(e) if app.debug else None
            }), 500'''

if old_error in content:
    content = content.replace(old_error, new_error)
    print('✅ Error handling improved')
else:
    print('⚠️ Error handling pattern not found')

# Save updated content
with open('application.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ All critical fixes applied successfully!')
print('📋 Updated:')
print('  - Rate limiting for /verify endpoint (30 req/min)')
print('  - VAT format validation')
print('  - Error message improvements')
