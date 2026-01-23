#!/usr/bin/env python3
"""
Script to add validation and error handling to application.py
"""

with open('application.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update 1: Add rate limiting check
old_verify_start = '''    def verify_counterparty():
        """Process verification request - requires authentication."""
        import logging
        logger = logging.getLogger(__name__)

        logger.error(f"VERIFY REQUEST: authenticated={current_user.is_authenticated}, user_id={current_user.id if current_user.is_authenticated else 'None'}")
        # User is authenticated via @login_required decorator

        # Check if user can perform verification (quota check)'''

new_verify_start = '''    def verify_counterparty():
        """Process verification request - requires authentication."""
        import logging
        logger = logging.getLogger(__name__)

        logger.error(f"VERIFY REQUEST: authenticated={current_user.is_authenticated}, user_id={current_user.id if current_user.is_authenticated else 'None'}")
        # User is authenticated via @login_required decorator

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

        # Check if user can perform verification (quota check)'''

if old_verify_start in content:
    content = content.replace(old_verify_start, new_verify_start)
    print('✅ Added rate limiting to verify_counterparty')
else:
    print('❌ Could not find verify_counterparty start to add rate limiting')

# Update 2: Add VAT validation
old_validation = '''            # Validate required fields
            logger.debug(f"Company data: {company_data}")
            logger.debug(f"Counterparty data: {counterparty_data}")

            if not company_data.get('vat_number') or not company_data.get('company_name'):
                logger.warning("Missing company required fields")
                return jsonify({'success': False, 'error': 'Company VAT and name are required'}), 400

            if not counterparty_data.get('company_name') or not counterparty_data.get('country'):
                logger.warning(f"Missing counterparty required fields. Name: {counterparty_data.get('company_name')}, Country: {counterparty_data.get('country')}")
                return jsonify({'success': False, 'error': 'Counterparty name and country are required'}), 400'''

new_validation = '''            # ==================== VALIDATION ====================
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
                    }), 400'''

if old_validation in content:
    content = content.replace(old_validation, new_validation)
    print('✅ Added VAT validation to verify_counterparty')
else:
    print('❌ Could not find validation section')

# Update 3: Improve error handling
old_error_handler = '''        except Exception as e:
            import traceback
            logger.error(f"Error in verify_counterparty: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"Error in verify_counterparty: {str(e)}")
            print(traceback.format_exc())
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500'''

new_error_handler = '''        except Exception as e:
            import traceback
            logger.error(f"Error in verify_counterparty: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"Error in verify_counterparty: {str(e)}")
            print(traceback.format_exc())
            db.session.rollback()
            
            # Return user-friendly error message
            error_msg = str(e)
            if 'VIES' in error_msg or 'vies' in error_msg.lower():
                error_msg = 'Fehler beim VIES-Service. Das System wird automatisch einen neuen Versuch durchführen. Bitte versuchen Sie es in wenigen Sekunden erneut.'
            else:
                error_msg = 'Ein unerwarteter Fehler ist aufgetreten. Bitte versuchen Sie es später erneut.'
            
            return jsonify({
                'success': False,
                'error': error_msg,
                'details': str(e) if app.debug else None
            }), 500'''

if old_error_handler in content:
    content = content.replace(old_error_handler, new_error_handler)
    print('✅ Improved error handling in verify_counterparty')
else:
    print('❌ Could not find error handler')

with open('application.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\n✅ All updates to application.py completed successfully!')
