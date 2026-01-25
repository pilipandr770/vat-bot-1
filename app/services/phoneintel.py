import os
import json
import subprocess
from typing import Dict, Any, List, Set

import phonenumbers
from phonenumbers import geocoder, carrier, number_type


class PhoneIntelService:
    """Analyze phone numbers for carrier, type, disposable/scam signals and a simple risk score.

    Important: This service does NOT perform any personal identification. It returns only
    metadata (country, carrier, line type, known scam flags, heuristics) and must not
    persist raw phone numbers. If storage is needed, hash or redact numbers externally.
    """

    def __init__(self):
        # Optional integration points. If PHONEINFOGA_BIN is set, tries to call local PhoneInfoga CLI.
        self.phoneinfoga_bin = os.environ.get('PHONEINFOGA_BIN')  # path to phoneinfoga executable
        self.phoneinfoga_url = os.environ.get('PHONEINFOGA_URL')  # optional service URL (not used by default)
        
        # Load scam databases for different countries
        self.scam_databases: Dict[str, Set[str]] = self._load_scam_databases()

    def _load_scam_databases(self) -> Dict[str, Set[str]]:
        """Load scam phone number databases for different countries."""
        databases = {}
        
        # US database (BlockGuard)
        us_db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'spam_database.txt')
        databases['us'] = self._load_single_database(us_db_path, 'US scam database')
        
        # French databases
        fr_db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'spam_database_fr.txt')
        databases['fr'] = self._load_single_database(fr_db_path, 'French scam database')
        
        # Add more countries here as needed
        # databases['de'] = self._load_single_database(german_db_path, 'German scam database')
        
        return databases

    def _load_single_database(self, db_path: str, db_name: str) -> Set[str]:
        """Load a single scam database file."""
        scam_numbers = set()
        
        try:
            if os.path.exists(db_path):
                with open(db_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and (line.startswith('+') or line[0].isdigit()):
                            # Handle both E164 format (+33123456789) and local format (0123456789)
                            if not line.startswith('+'):
                                line = '+' + line
                            scam_numbers.add(line)
                print(f"✅ Loaded {db_name}: {len(scam_numbers)} numbers")
            else:
                print(f"⚠️  {db_name} not found at {db_path}")
        except Exception as e:
            print(f"❌ Error loading {db_name}: {e}")
        
        return scam_numbers

    def analyze(self, raw_number: str, country_hint: str = None) -> Dict[str, Any]:
        # Parse with phonenumbers
        result: Dict[str, Any] = {
            'country': None,
            'carrier': None,
            'line_type': 'unknown',
            'disposable': False,
            'seen_in_scam_db': False,
            'suspicious_patterns': [],
            'risk_score': 0,
            'verdict': 'unknown'
        }

        try:
            if country_hint:
                parsed = phonenumbers.parse(raw_number, country_hint.upper())
            else:
                parsed = phonenumbers.parse(raw_number)
            
            # Validate it's a valid number
            if not phonenumbers.is_valid_number(parsed):
                result['verdict'] = 'invalid'
                result['risk_score'] = 100
                return result

            # Country display name
            try:
                result['country'] = geocoder.description_for_number(parsed, 'en')
            except Exception:
                result['country'] = None

            # Carrier name
            try:
                result['carrier'] = carrier.name_for_number(parsed, 'en')
            except Exception:
                result['carrier'] = None

            # Line type
            t = number_type(parsed)
            if t in (phonenumbers.PhoneNumberType.MOBILE, phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE):
                result['line_type'] = 'mobile'
            elif t == phonenumbers.PhoneNumberType.FIXED_LINE:
                result['line_type'] = 'fixed'
            elif t == phonenumbers.PhoneNumberType.VOIP:
                result['line_type'] = 'voip'
            elif t == phonenumbers.PhoneNumberType.PREMIUM_RATE:
                result['line_type'] = 'premium'
            else:
                result['line_type'] = 'unknown'

            national_number = str(parsed.national_number)

            # Check against scam databases by country
            e164_number = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            country_code = parsed.country_code
            
            # Check country-specific database
            country_key = None
            if country_code == 1:  # US/Canada
                country_key = 'us'
            elif country_code == 33:  # France
                country_key = 'fr'
            # Add more countries as needed
            
            if country_key and country_key in self.scam_databases:
                if e164_number in self.scam_databases[country_key]:
                    result['seen_in_scam_db'] = True
                    result['suspicious_patterns'].append(f'reported-in-{country_key}-scam-database')
            
            # Also check if number matches any pattern in French database (for French numbers)
            if country_code == 33 and 'fr' in self.scam_databases:
                national_number = str(parsed.national_number)
                for scam_pattern in self.scam_databases['fr']:
                    if scam_pattern.endswith('?'):
                        # Handle pattern matching (e.g., "+33162?" matches numbers starting with 162)
                        if scam_pattern.startswith('+33'):
                            # Extract the pattern part after country code
                            pattern_base = scam_pattern[3:-1]  # Remove +33 and ?
                            if national_number.startswith(pattern_base):
                                result['seen_in_scam_db'] = True
                                result['suspicious_patterns'].append('matches-french-spam-pattern')
                                break

            # Heuristics / suspicious patterns (simple examples)
            if national_number.startswith('700') or national_number.startswith('900'):
                result['suspicious_patterns'].append('premium-rate-prefix')

            if len(national_number) <= 6:
                result['suspicious_patterns'].append('short-number')

        except phonenumbers.NumberParseException:
            result['verdict'] = 'invalid'
            result['risk_score'] = 100
            return result

        # Optional: try calling local PhoneInfoga CLI if available for deeper signals
        if self.phoneinfoga_bin:
            try:
                proc = subprocess.run(
                    [self.phoneinfoga_bin, 'scan', raw_number, '--format', 'json'],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if proc.returncode == 0 and proc.stdout:
                    try:
                        pi = json.loads(proc.stdout)
                        # Map fields if present
                        if isinstance(pi, dict):
                            # The structure depends on the PhoneInfoga version; handle gracefully
                            result['seen_in_scam_db'] = pi.get('seen', result['seen_in_scam_db']) or pi.get('scam', result['seen_in_scam_db'])
                            # Accept carrier/line info if provided
                            result['carrier'] = pi.get('carrier') or result['carrier']
                            result['line_type'] = pi.get('line_type') or result['line_type']
                            # Flags
                            if pi.get('disposable'):
                                result['disposable'] = True
                            if pi.get('notes') and isinstance(pi.get('notes'), list):
                                result['suspicious_patterns'].extend(pi.get('notes'))
                    except Exception:
                        pass
            except Exception:
                # Don't fail the overall analysis on CLI call errors
                pass

        # Combine heuristics into a simple risk score
        score = 0
        if result['seen_in_scam_db']:
            score += 70
        if result['disposable']:
            score += 20
        score += min(10 * len(result['suspicious_patterns']), 30)
        score = min(score, 100)
        result['risk_score'] = score

        if score >= 70:
            result['verdict'] = 'high'
        elif score >= 30:
            result['verdict'] = 'medium'
        else:
            result['verdict'] = 'low'

        return result


def get_service() -> PhoneIntelService:
    return PhoneIntelService()
