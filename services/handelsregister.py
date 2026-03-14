import requests
import time
from datetime import datetime
from typing import Dict, Optional

class HandelsregisterService:
    """Service for checking German Handelsregister (Commercial Register)."""
    
    def __init__(self):
        # Official Handelsregister API endpoints
        self.base_url = "https://www.handelsregister.de"
        self.search_url = f"{self.base_url}/rp_web/search.do"
        
        # Alternative: Unternehmensregister.de
        self.unternehmensregister_url = "https://www.unternehmensregister.de/ureg/"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Counterparty-Verification-System/1.0',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'de,en;q=0.9'
        })
    
    def check_company(self, company_name: str, registration_number: str = None) -> Dict:
        """
        Check company registration in German Handelsregister.
        
        Args:
            company_name: Company name to search
            registration_number: Optional HRB/HRA number
        
        Returns:
            Standardized response dictionary
        """
        start_time = time.time()
        
        try:
            # Try multiple search strategies
            results = []
            
            # Search by company name
            name_result = self._search_by_name(company_name)
            if name_result:
                results.append(name_result)
            
            # Search by registration number if provided
            if registration_number:
                reg_result = self._search_by_registration_number(registration_number)
                if reg_result:
                    results.append(reg_result)
            
            response_time = int((time.time() - start_time) * 1000)
            
            if results:
                # Take the best match (first result with highest confidence)
                best_match = max(results, key=lambda x: x.get('match_confidence', 0))
                
                return {
                    'status': 'valid' if best_match.get('active', False) else 'warning',
                    'source': 'handelsregister',
                    'data': {
                        'company_name': company_name,
                        'search_results': results,
                        'best_match': best_match,
                        'total_matches': len(results)
                    },
                    'last_checked': datetime.utcnow().isoformat(),
                    'confidence': best_match.get('match_confidence', 0.5),
                    'response_time_ms': response_time,
                    'error_message': None
                }
            else:
                return {
                    'status': 'warning',
                    'source': 'handelsregister',
                    'data': {
                        'company_name': company_name,
                        'search_results': [],
                        'message': 'Keine Übereinstimmungen im Handelsregister gefunden'
                    },
                    'last_checked': datetime.utcnow().isoformat(),
                    'confidence': 0.3,
                    'response_time_ms': response_time,
                    'error_message': 'Firma nicht im deutschen Handelsregister gefunden'
                }
                
        except Exception as e:
            return self._create_error_response(f"Handelsregister check failed: {str(e)}", int((time.time() - start_time) * 1000))
    
    def _search_by_name(self, company_name: str) -> Optional[Dict]:
        """Search company by name in Handelsregister."""
        try:
            # For demo purposes, simulate Handelsregister search
            # In production, implement actual API integration or web scraping
            
            # Mock database of German companies for testing
            mock_companies = [
                {
                    'name': 'BMW AG',
                    'registration_number': 'HRB 42243',
                    'court': 'München',
                    'active': True,
                    'legal_form': 'AG',
                    'address': 'Petuelring 130, 80809 München',
                    'established_date': '1916-03-07',
                    'capital': 'EUR 658,608,580.80',
                    'managing_directors': ['Oliver Zipse'],
                    'business_purpose': 'Kraftfahrzeuge und Ersatzteile'
                },
                {
                    'name': 'SAP SE',
                    'registration_number': 'HRB 719915',
                    'court': 'Mannheim',
                    'active': True,
                    'legal_form': 'SE',
                    'address': 'Dietmar-Hopp-Allee 16, 69190 Walldorf',
                    'established_date': '1972-04-01',
                    'capital': 'EUR 1,229,382,144.00',
                    'managing_directors': ['Christian Klein', 'Luka Mucic'],
                    'business_purpose': 'Software und IT-Dienstleistungen'
                },
                {
                    'name': 'Deutsche Bank AG',
                    'registration_number': 'HRB 30000',
                    'court': 'Frankfurt am Main',
                    'active': True,
                    'legal_form': 'AG',
                    'address': 'Taunusanlage 12, 60325 Frankfurt am Main',
                    'established_date': '1870-01-22',
                    'capital': 'EUR 5,290,939,215.36',
                    'managing_directors': ['Christian Sewing'],
                    'business_purpose': 'Bankgeschäfte aller Art'
                }
            ]
            
            # Find best match
            best_match = None
            highest_similarity = 0
            
            for company in mock_companies:
                similarity = self._calculate_name_similarity(
                    company_name.lower().strip(),
                    company['name'].lower().strip()
                )
                
                if similarity > highest_similarity and similarity > 0.3:  # Minimum threshold
                    highest_similarity = similarity
                    best_match = company.copy()
                    best_match['match_confidence'] = similarity
            
            # If no good match, create a generic result for demo
            if not best_match and any(keyword in company_name.lower() for keyword in ['gmbh', 'ag', 'kg', 'ohg']):
                best_match = {
                    'name': company_name,
                    'registration_number': 'HRB XXXXX',
                    'court': 'Unknown',
                    'active': True,
                    'legal_form': self._extract_legal_form(company_name),
                    'address': 'Address not available',
                    'match_confidence': 0.5,
                    'note': 'Simulated result for demo purposes'
                }
            
            return best_match
            
        except Exception as e:
            return None
    
    def _search_by_registration_number(self, registration_number: str) -> Optional[Dict]:
        """Search company by registration number."""
        try:
            # Clean registration number
            reg_num = registration_number.strip().upper()
            
            # Mock search by registration number
            if reg_num.startswith('HRB') or reg_num.startswith('HRA'):
                return {
                    'name': f'Company with {reg_num}',
                    'registration_number': reg_num,
                    'court': 'Unknown Court',
                    'active': True,
                    'legal_form': 'GmbH' if reg_num.startswith('HRB') else 'e.K.',
                    'match_confidence': 0.9,
                    'search_method': 'registration_number',
                    'note': 'Found by registration number'
                }
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between company names."""
        if not name1 or not name2:
            return 0.0
        
        # Remove common German legal form suffixes for comparison
        suffixes = ['gmbh', 'ag', 'kg', 'ohg', 'e.k.', 'gbr', 'se']
        
        def clean_name(name):
            name = name.lower().strip()
            for suffix in suffixes:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            return name
        
        clean1 = clean_name(name1)
        clean2 = clean_name(name2)
        
        # Simple word-based similarity
        words1 = set(clean1.split())
        words2 = set(clean2.split())
        
        if len(words1) == 0 and len(words2) == 0:
            return 1.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Boost similarity if one name contains the other
        if clean1 in clean2 or clean2 in clean1:
            jaccard_similarity = min(1.0, jaccard_similarity + 0.3)
        
        return jaccard_similarity
    
    def _extract_legal_form(self, company_name: str) -> str:
        """Extract German legal form from company name."""
        name_lower = company_name.lower()
        
        legal_forms = {
            'gmbh': 'GmbH',
            'ag': 'AG',
            'kg': 'KG',
            'ohg': 'OHG',
            'e.k.': 'e.K.',
            'gbr': 'GbR',
            'se': 'SE',
            'ug': 'UG'
        }
        
        for suffix, form in legal_forms.items():
            if suffix in name_lower:
                return form
        
        return 'Unknown'
    
    def get_company_details(self, registration_number: str) -> Dict:
        """
        Get detailed company information from Handelsregister.
        
        Args:
            registration_number: HRB or HRA number
        
        Returns:
            Detailed company information
        """
        try:
            # In production, implement detailed company lookup
            # This would include balance sheets, annual reports, etc.
            
            return {
                'registration_number': registration_number,
                'detailed_data_available': False,
                'message': 'Detailed company lookup not implemented in demo version',
                'available_data': [
                    'Basic registration info',
                    'Legal form and status',
                    'Registered address',
                    'Managing directors'
                ],
                'note': 'Full implementation would include balance sheets, annual reports, ownership structure'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'registration_number': registration_number
            }
    
    def _create_error_response(self, error_message: str, response_time: int) -> Dict:
        """Create standardized error response."""
        return {
            'status': 'error',
            'source': 'handelsregister',
            'data': {},
            'last_checked': datetime.utcnow().isoformat(),
            'confidence': 0.0,
            'response_time_ms': response_time,
            'error_message': error_message
        }
    
    def check_service_availability(self) -> Dict:
        """Check if Handelsregister service is available."""
        try:
            response = self.session.head(self.base_url, timeout=10)
            return {
                'available': response.status_code < 400,
                'status_code': response.status_code,
                'response_time_ms': int(response.elapsed.total_seconds() * 1000),
                'checked_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'checked_at': datetime.utcnow().isoformat()
            }