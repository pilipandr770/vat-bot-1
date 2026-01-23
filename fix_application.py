"""
Update application.py with critical fixes:
1. Rate limiting
2. VAT validation
3. Better error handling
"""

def add_rate_limiting_and_validation():
    with open('application.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and modify verify_counterparty function
    modified_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        modified_lines.append(line)
        
        # Add rate limiting after "# User is authenticated via @login_required decorator"
        if '# User is authenticated via @login_required decorator' in line:
            # Find the next non-empty line after this
            i += 1
            modified_lines.append(lines[i])  # blank line
            
            # Add rate limiting block
            rate_limit_code = '''
        # ==================== RATE LIMITING ====================
        identifier = f"user_{current_user.id}"
        allowed_min, info_min = rate_limiter.is_allowed(identifier, 30, 60)  # 30 req/min
        if not allowed_min:
            logger.warning(f"Rate limit exceeded for user {current_user.id}")
            return jsonify({
                'success': False,
                'error': f'Zu viele Anfragen. Bitte warten Sie {info_min["retry_after"]} Sekunden bevor Sie es erneut versuchen.',
                'rate_limit': True,
                'retry_after': info_min['retry_after']
            }), 429

'''
            modified_lines.append(rate_limit_code)
        
        # Replace validation section
        elif '# Validate required fields' in line:
            modified_lines.pop()  # Remove the line we just added
            
            validation_code = '''            # ==================== VALIDATION ====================
            logger.debug(f"Company data: {company_data}")
            logger.debug(f"Counterparty data: {counterparty_data}")

            # Validate company data
            if not company_data.get('vat_number') or not company_data.get('company_name'):
                logger.warning("Missing company required fields")
                return jsonify({
                    'success': False,
                    'error': 'Firma VAT und Name sind erforderlich',
                    'field': 'company'
                }), 400

            # Validate company VAT format
            company_country = 'DE'  # Default to Germany
            is_valid_company_vat, company_vat_error, _ = validate_vat_format(
                company_country,
                company_data['vat_number']
            )
            if not is_valid_company_vat:
                logger.warning(f"Invalid company VAT format: {company_vat_error}")
                return jsonify({
                    'success': False,
                    'error': f'Ungültige Firma VAT-Nummer: {company_vat_error}',
                    'field': 'company_vat'
                }), 400

            # Validate counterparty data
            if not counterparty_data.get('company_name') or not counterparty_data.get('country'):
                logger.warning(f"Missing counterparty required fields. Name: {counterparty_data.get('company_name')}, Country: {counterparty_data.get('country')}")
                return jsonify({
                    'success': False,
                    'error': 'Geschäftspartner Name und Land sind erforderlich',
                    'field': 'counterparty'
                }), 400

            # Validate counterparty VAT if provided
            if counterparty_data.get('vat_number'):
                is_valid_vat, vat_error, _ = validate_vat_format(
                    counterparty_data['country'],
                    counterparty_data['vat_number']
                )
                if not is_valid_vat:
                    logger.warning(f"Invalid counterparty VAT format: {vat_error}")
                    return jsonify({
                        'success': False,
                        'error': f'Ungültige Geschäftspartner VAT-Nummer: {vat_error}',
                        'field': 'counterparty_vat'
                    }), 400

'''
            modified_lines.append(validation_code)
            
            # Skip old validation lines (until we hit "if not company_data.get")
            while i < len(lines) and 'if not company_data.get' not in lines[i]:
                i += 1
            i -= 1  # Back up one since the loop will increment
        
        i += 1
    
    with open('application.py', 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)
    
    print('✅ Updated application.py with validation and rate limiting')


if __name__ == '__main__':
    add_rate_limiting_and_validation()
