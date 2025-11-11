import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VIESService:
    """VIES (VAT Information Exchange System) service integration with retry logic and caching."""
    
    def __init__(self):
        self.base_url = "http://ec.europa.eu/taxation_customs/vies/services/checkVatService"
        self.soap_action = "checkVat"
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        self._cache = {}  # Simple in-memory cache: {vat_key: (result, expiry_time)}
        self.cache_ttl = 3600  # 1 hour cache
        
    def validate_vat(self, country_code: str, vat_number: str) -> Dict:
        """
        Validate VAT number through VIES service with retry logic and caching.
        
        Args:
            country_code: 2-letter country code (e.g., 'DE', 'AT')
            vat_number: VAT number without country prefix
        
        Returns:
            Standardized response dictionary
        """
        # Check cache first
        cache_key = f"{country_code.upper()}:{vat_number}"
        cached_result = self._get_cached(cache_key)
        if cached_result:
            logger.info(f"VIES cache hit for {cache_key}")
            return cached_result
        
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Clean VAT number (remove country prefix if present)
                clean_vat = self._clean_vat_number(vat_number, country_code)
                
                # Prepare SOAP request
                soap_envelope = self._build_soap_request(country_code, clean_vat)
                
                # Make request
                headers = {
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': self.soap_action
                }
                
                response = requests.post(
                    self.base_url,
                    data=soap_envelope,
                    headers=headers,
                    timeout=30
                )
                
                response_time = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    result = self._parse_vies_response(response.text, response_time)
                    
                    # Check if we got MS_MAX_CONCURRENT_REQ error
                    if result.get('status') == 'error' and 'MS_MAX_CONCURRENT_REQ' in str(result.get('error_message', '')):
                        last_error = result
                        if attempt < self.max_retries - 1:
                            # Exponential backoff: 2s, 4s, 8s
                            delay = self.retry_delay * (2 ** attempt)
                            logger.warning(f"VIES rate limit hit, retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                            time.sleep(delay)
                            continue
                    
                    # Cache successful results (including errors to avoid hammering VIES)
                    self._set_cache(cache_key, result)
                    return result
                else:
                    return self._create_error_response(
                        f"VIES API error: HTTP {response.status_code}",
                        response_time
                    )
                    
            except requests.exceptions.Timeout:
                return self._create_error_response("VIES service timeout", int((time.time() - start_time) * 1000))
            
            except requests.exceptions.ConnectionError:
                return self._create_error_response("Cannot connect to VIES service", int((time.time() - start_time) * 1000))
            
            except Exception as e:
                last_error = self._create_error_response(f"VIES validation error: {str(e)}", int((time.time() - start_time) * 1000))
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"VIES error, retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                    continue
        
        # All retries exhausted
        return last_error or self._create_error_response("VIES service unavailable after retries", int((time.time() - start_time) * 1000))
    
    def _clean_vat_number(self, vat_number: str, country_code: str) -> str:
        """Remove country prefix and clean VAT number."""
        vat = vat_number.strip().upper()
        
        # Remove country prefix if present
        if vat.startswith(country_code.upper()):
            vat = vat[len(country_code):]
        
        # Remove common prefixes
        if vat.startswith('VAT'):
            vat = vat[3:]
        
        return vat.strip()
    
    def _build_soap_request(self, country_code: str, vat_number: str) -> str:
        """Build SOAP XML request for VIES."""
        return f"""<?xml version="1.0" encoding="UTF-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:tns1="urn:ec.europa.eu:taxud:vies:services:checkVat:types">
            <soap:Header>
            </soap:Header>
            <soap:Body>
                <tns1:checkVat>
                    <tns1:countryCode>{country_code.upper()}</tns1:countryCode>
                    <tns1:vatNumber>{vat_number}</tns1:vatNumber>
                </tns1:checkVat>
            </soap:Body>
        </soap:Envelope>"""
    
    def _parse_vies_response(self, response_xml: str, response_time: int) -> Dict:
        """Parse SOAP XML response from VIES."""
        try:
            # Simple XML parsing (in production, use proper XML parser)
            if '<soap:Fault>' in response_xml or '<faultstring>' in response_xml:
                # Extract fault message
                fault_start = response_xml.find('<faultstring>')
                fault_end = response_xml.find('</faultstring>')
                if fault_start != -1 and fault_end != -1:
                    fault_message = response_xml[fault_start+13:fault_end]
                    return self._create_error_response(f"VIES fault: {fault_message}", response_time)
            
            # Check if VAT is valid
            valid = '<ns2:valid>true</ns2:valid>' in response_xml
            
            # Extract company name and address if available
            company_name = self._extract_xml_value(response_xml, 'name')
            company_address = self._extract_xml_value(response_xml, 'address')
            
            data = {
                'country_code': self._extract_xml_value(response_xml, 'countryCode'),
                'vat_number': self._extract_xml_value(response_xml, 'vatNumber'),
                'valid': valid,
                'company_name': company_name,
                'company_address': company_address,
                'request_date': datetime.utcnow().isoformat()
            }
            
            # Determine status and confidence
            if valid:
                status = 'valid'
                confidence = 0.95 if company_name else 0.85
            else:
                status = 'error'
                confidence = 0.1
            
            return {
                'status': status,
                'source': 'vies',
                'data': data,
                'last_checked': datetime.utcnow().isoformat(),
                'confidence': confidence,
                'response_time_ms': response_time,
                'error_message': None
            }
            
        except Exception as e:
            return self._create_error_response(f"Error parsing VIES response: {str(e)}", response_time)
    
    def _extract_xml_value(self, xml: str, tag: str) -> Optional[str]:
        """Extract value from XML tag."""
        start_tag = f'<ns2:{tag}>'
        end_tag = f'</ns2:{tag}>'
        
        start = xml.find(start_tag)
        if start == -1:
            return None
        
        start += len(start_tag)
        end = xml.find(end_tag, start)
        if end == -1:
            return None
        
        value = xml[start:end].strip()
        return value if value else None
    
    def _create_error_response(self, error_message: str, response_time: int) -> Dict:
        """Create standardized error response."""
        return {
            'status': 'error',
            'source': 'vies',
            'data': {},
            'last_checked': datetime.utcnow().isoformat(),
            'confidence': 0.0,
            'response_time_ms': response_time,
            'error_message': error_message
        }
    
    def validate_vat_format(self, country_code: str, vat_number: str) -> Dict:
        """
        Validate VAT number format without calling VIES API.
        Useful for pre-validation.
        """
        patterns = {
            'AT': r'^ATU[0-9]{8}$',
            'BE': r'^BE[0-9]{10}$',
            'BG': r'^BG[0-9]{9,10}$',
            'CY': r'^CY[0-9]{8}[A-Z]$',
            'CZ': r'^CZ[0-9]{8,10}$',
            'DE': r'^DE[0-9]{9}$',
            'DK': r'^DK[0-9]{8}$',
            'EE': r'^EE[0-9]{9}$',
            'EL': r'^EL[0-9]{9}$',
            'ES': r'^ES[0-9A-Z][0-9]{7}[0-9A-Z]$',
            'FI': r'^FI[0-9]{8}$',
            'FR': r'^FR[0-9A-Z]{2}[0-9]{9}$',
            'GB': r'^GB([0-9]{9}([0-9]{3})?|[A-Z]{2}[0-9]{3})$',
            'HR': r'^HR[0-9]{11}$',
            'HU': r'^HU[0-9]{8}$',
            'IE': r'^IE[0-9]{7}[A-Z]{1,2}$',
            'IT': r'^IT[0-9]{11}$',
            'LT': r'^LT([0-9]{9}|[0-9]{12})$',
            'LU': r'^LU[0-9]{8}$',
            'LV': r'^LV[0-9]{11}$',
            'MT': r'^MT[0-9]{8}$',
            'NL': r'^NL[0-9]{9}B[0-9]{2}$',
            'PL': r'^PL[0-9]{10}$',
            'PT': r'^PT[0-9]{9}$',
            'RO': r'^RO[0-9]{2,10}$',
            'SE': r'^SE[0-9]{12}$',
            'SI': r'^SI[0-9]{8}$',
            'SK': r'^SK[0-9]{10}$'
        }
        
        import re
        
        full_vat = f"{country_code.upper()}{self._clean_vat_number(vat_number, country_code)}"
        pattern = patterns.get(country_code.upper())
        
        if not pattern:
            return {
                'valid': False,
                'message': f'VAT format validation not supported for country: {country_code}'
            }
        
        is_valid = bool(re.match(pattern, full_vat))
        
        return {
            'valid': is_valid,
            'message': 'Valid format' if is_valid else f'Invalid VAT format for {country_code}',
            'pattern': pattern,
            'formatted_vat': full_vat
        }
    def _get_cached(self, key: str) -> Optional[Dict]:
        """Get cached VIES result if not expired."""
        if key in self._cache:
            result, expiry = self._cache[key]
            if datetime.now() < expiry:
                return result
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None
    
    def _set_cache(self, key: str, result: Dict) -> None:
        """Cache VIES result with TTL."""
        expiry = datetime.now() + timedelta(seconds=self.cache_ttl)
        self._cache[key] = (result, expiry)
        
        # Simple cache cleanup: remove expired entries if cache grows too large
        if len(self._cache) > 1000:
            now = datetime.now()
            self._cache = {k: v for k, v in self._cache.items() if v[1] > now}
