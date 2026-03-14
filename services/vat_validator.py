"""
VAT validation utilities for improved error handling and user feedback.
"""
import re
from typing import Dict, Tuple, Optional


VAT_FORMATS = {
    'AT': {'pattern': r'^AT?U?[0-9]{8}$', 'length': 10, 'description': 'ATU12345678'},
    'BE': {'pattern': r'^BE?[0-9]{10}$', 'length': 10, 'description': 'BE1234567890'},
    'BG': {'pattern': r'^BG?[0-9]{9,10}$', 'length': 10, 'description': 'BG1234567890'},
    'CY': {'pattern': r'^CY?[0-9]{8}[A-Z]$', 'length': 9, 'description': 'CY12345678A'},
    'CZ': {'pattern': r'^CZ?[0-9]{8,10}$', 'length': 10, 'description': 'CZ12345678'},
    'DE': {'pattern': r'^DE?[0-9]{9}$', 'length': 11, 'description': 'DE123456789'},
    'DK': {'pattern': r'^DK?[0-9]{8}$', 'length': 10, 'description': 'DK12345678'},
    'EE': {'pattern': r'^EE?[0-9]{9}$', 'length': 11, 'description': 'EE123456789'},
    'EL': {'pattern': r'^EL?[0-9]{9}$', 'length': 11, 'description': 'EL123456789'},
    'ES': {'pattern': r'^ES?[0-9A-Z][0-9]{7}[0-9A-Z]$', 'length': 9, 'description': 'ES12345678A'},
    'FI': {'pattern': r'^FI?[0-9]{8}$', 'length': 10, 'description': 'FI12345678'},
    'FR': {'pattern': r'^FR?[0-9A-Z]{2}[0-9]{9}$', 'length': 13, 'description': 'FR12AB123456789'},
    'GB': {'pattern': r'^GB?([0-9]{9}([0-9]{3})?|[A-Z]{2}[0-9]{3})$', 'length': 11, 'description': 'GB123456789'},
    'HR': {'pattern': r'^HR?[0-9]{11}$', 'length': 13, 'description': 'HR12345678901'},
    'HU': {'pattern': r'^HU?[0-9]{8}$', 'length': 10, 'description': 'HU12345678'},
    'IE': {'pattern': r'^IE?[0-9]{7}[A-Z]{1,2}$', 'length': 9, 'description': 'IE1234567AB'},
    'IT': {'pattern': r'^IT?[0-9]{11}$', 'length': 13, 'description': 'IT12345678901'},
    'LT': {'pattern': r'^LT?([0-9]{9}|[0-9]{12})$', 'length': 12, 'description': 'LT123456789'},
    'LU': {'pattern': r'^LU?[0-9]{8}$', 'length': 10, 'description': 'LU12345678'},
    'LV': {'pattern': r'^LV?[0-9]{11}$', 'length': 13, 'description': 'LV12345678901'},
    'MT': {'pattern': r'^MT?[0-9]{8}$', 'length': 10, 'description': 'MT12345678'},
    'NL': {'pattern': r'^NL?[0-9]{9}B[0-9]{2}$', 'length': 12, 'description': 'NL123456789B01'},
    'PL': {'pattern': r'^PL?[0-9]{10}$', 'length': 12, 'description': 'PL1234567890'},
    'PT': {'pattern': r'^PT?[0-9]{9}$', 'length': 11, 'description': 'PT123456789'},
    'RO': {'pattern': r'^RO?[0-9]{2,10}$', 'length': 10, 'description': 'RO1234567890'},
    'SE': {'pattern': r'^SE?[0-9]{12}$', 'length': 14, 'description': 'SE123456789012'},
    'SI': {'pattern': r'^SI?[0-9]{8}$', 'length': 10, 'description': 'SI12345678'},
    'SK': {'pattern': r'^SK?[0-9]{10}$', 'length': 12, 'description': 'SK1234567890'},
}


def validate_vat_format(country_code: str, vat_number: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate VAT number format for a given country.

    Args:
        country_code: 2-letter country code (e.g., 'DE', 'AT')
        vat_number: VAT number (with or without country prefix)

    Returns:
        Tuple of (is_valid, error_message or 'Valid', formatted_vat)
    """
    if not country_code or not vat_number:
        return False, 'Land und VAT-Nummer sind erforderlich', None

    country_code = country_code.strip().upper()
    vat_number = vat_number.strip().upper()

    # Check if country is supported
    if country_code not in VAT_FORMATS:
        return False, f'VAT-Validierung für Land "{country_code}" wird nicht unterstützt', None

    # Clean VAT number (remove country prefix and spaces)
    vat_clean = vat_number.replace(country_code, '', 1).replace(' ', '').strip()

    # Build full VAT with country code
    full_vat = f"{country_code}{vat_clean}"

    # Validate against pattern
    pattern = VAT_FORMATS[country_code]['pattern']
    if not re.match(pattern, full_vat):
        expected_format = VAT_FORMATS[country_code]['description']
        return False, (
            f'Ungültiges VAT-Format für {country_code}. '
            f'Erwartet: {expected_format} (erhalten: {full_vat})'
        ), full_vat

    return True, 'Valid', full_vat


def get_vat_format_hint(country_code: str) -> str:
    """Get example VAT format for a country."""
    if country_code and country_code.upper() in VAT_FORMATS:
        return VAT_FORMATS[country_code.upper()]['description']
    return 'Beispiel: DE123456789'


def validate_counterparty_data(data: Dict) -> Tuple[bool, Optional[str]]:
    """
    Validate complete counterparty data for verification.

    Args:
        data: Dict with counterparty data

    Returns:
        Tuple of (is_valid, error_message or None)
    """
    required_fields = ['company_name', 'country']
    optional_vat = data.get('vat_number')
    country = data.get('country', '').strip().upper()

    # Check required fields
    for field in required_fields:
        if not data.get(field, '').strip():
            return False, f'{field} ist erforderlich'

    # Validate VAT if provided
    if optional_vat:
        is_valid, error_msg, _ = validate_vat_format(country, optional_vat)
        if not is_valid:
            return False, error_msg

    return True, None
