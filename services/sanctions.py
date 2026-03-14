import requests
import time
from datetime import datetime
from typing import Dict, List, Optional

class SanctionsService:
    """Service for checking EU, OFAC, and UK sanctions lists."""
    
    def __init__(self):
        # EU Sanctions endpoints
        self.eu_sanctions_url = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList/content"
        
        # OFAC endpoints
        self.ofac_sdn_url = "https://www.treasury.gov/ofac/downloads/sdn.xml"
        self.ofac_consolidated_url = "https://api.trade.gov/consolidated_screening_list/search"
        
        # UK HM Treasury sanctions
        self.uk_sanctions_url = "https://ofsistorage.blob.core.windows.net/publishlive/2022format/ConList.json"
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Counterparty-Verification-System/1.0'
        })
    
    def check_sanctions(self, company_name: str, person_name: str = "") -> Dict:
        """
        Check company and person names against multiple sanctions lists.
        
        Args:
            company_name: Company name to check
            person_name: Person name to check (optional)
        
        Returns:
            Standardized response dictionary
        """
        start_time = time.time()
        
        try:
            results = {
                'eu_sanctions': self._check_eu_sanctions(company_name, person_name),
                'ofac_sanctions': self._check_ofac_sanctions(company_name, person_name),
                'uk_sanctions': self._check_uk_sanctions(company_name, person_name)
            }
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Analyze combined results
            sanctions_found = []
            highest_confidence = 0.0
            
            for source, result in results.items():
                if result.get('matches'):
                    sanctions_found.extend([
                        {
                            'source': source,
                            'match': match,
                            'confidence': result.get('confidence', 0.5)
                        }
                        for match in result['matches']
                    ])
                    highest_confidence = max(highest_confidence, result.get('confidence', 0.5))
            
            # Determine overall status
            if sanctions_found:
                status = 'error'  # Critical - sanctions found
                confidence = highest_confidence
            else:
                status = 'valid'  # No sanctions found
                confidence = 0.9  # High confidence in clear result
            
            return {
                'status': status,
                'source': 'sanctions',
                'data': {
                    'company_name': company_name,
                    'person_name': person_name,
                    'sanctions_found': sanctions_found,
                    'total_matches': len(sanctions_found),
                    'checked_sources': list(results.keys()),
                    'detailed_results': results
                },
                'last_checked': datetime.utcnow().isoformat(),
                'confidence': confidence,
                'response_time_ms': response_time,
                'error_message': None
            }
            
        except Exception as e:
            return self._create_error_response(f"Sanctions check failed: {str(e)}", int((time.time() - start_time) * 1000))
    
    def _check_eu_sanctions(self, company_name: str, person_name: str) -> Dict:
        """Check against EU consolidated sanctions list."""
        try:
            # For demo purposes, simulate API call with mock data
            # In production, implement actual EU sanctions API integration
            
            # Mock suspicious names for testing
            suspicious_companies = [
                'sanctioned company',
                'blocked enterprise',
                'restricted trading'
            ]
            
            matches = []
            
            # Simple substring matching (in production, use fuzzy matching)
            for suspicious in suspicious_companies:
                if suspicious.lower() in company_name.lower():
                    matches.append({
                        'type': 'company',
                        'name': suspicious,
                        'match_score': 0.8,
                        'list_type': 'EU Consolidated List',
                        'reason': 'Economic sanctions'
                    })
            
            return {
                'matches': matches,
                'confidence': 0.85 if matches else 0.9,
                'source_available': True
            }
            
        except Exception as e:
            return {
                'matches': [],
                'confidence': 0.0,
                'source_available': False,
                'error': str(e)
            }
    
    def _check_ofac_sanctions(self, company_name: str, person_name: str) -> Dict:
        """Check against US OFAC sanctions lists."""
        try:
            # Use Trade.gov Consolidated Screening List API
            params = {
                'q': company_name,
                'sources': 'SDN,EL,FSE',  # SDN List, Entity List, Foreign Sanctions Evaders
                'size': 10
            }
            
            response = self.session.get(
                self.ofac_consolidated_url,
                params=params,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                matches = []
                
                for result in data.get('results', []):
                    match_score = self._calculate_name_similarity(
                        company_name.lower(),
                        result.get('name', '').lower()
                    )
                    
                    if match_score > 0.7:  # High similarity threshold
                        matches.append({
                            'type': 'company',
                            'name': result.get('name'),
                            'match_score': match_score,
                            'list_type': result.get('source'),
                            'reason': result.get('title', 'OFAC sanctions'),
                            'addresses': result.get('addresses', []),
                            'alt_names': result.get('alt_names', [])
                        })
                
                return {
                    'matches': matches,
                    'confidence': 0.9,
                    'source_available': True,
                    'total_results': len(data.get('results', []))
                }
            else:
                return {
                    'matches': [],
                    'confidence': 0.5,  # Reduced confidence due to API error
                    'source_available': False,
                    'error': f'OFAC API returned status {response.status_code}'
                }
                
        except Exception as e:
            return {
                'matches': [],
                'confidence': 0.0,
                'source_available': False,
                'error': str(e)
            }
    
    def _check_uk_sanctions(self, company_name: str, person_name: str) -> Dict:
        """Check against UK HM Treasury sanctions."""
        try:
            # Mock implementation for UK sanctions
            # In production, integrate with actual UK sanctions API
            
            matches = []
            
            # Simple demo logic
            uk_keywords = ['london laundering', 'uk prohibited', 'british blocked']
            
            for keyword in uk_keywords:
                if keyword.lower() in company_name.lower():
                    matches.append({
                        'type': 'company',
                        'name': keyword,
                        'match_score': 0.75,
                        'list_type': 'UK Financial Sanctions',
                        'reason': 'UK Treasury sanctions'
                    })
            
            return {
                'matches': matches,
                'confidence': 0.85,
                'source_available': True
            }
            
        except Exception as e:
            return {
                'matches': [],
                'confidence': 0.0,
                'source_available': False,
                'error': str(e)
            }
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two names using simple algorithm.
        In production, use more sophisticated fuzzy matching (e.g., fuzzywuzzy).
        """
        if not name1 or not name2:
            return 0.0
        
        # Simple Jaccard similarity for demo
        set1 = set(name1.lower().split())
        set2 = set(name2.lower().split())
        
        if len(set1) == 0 and len(set2) == 0:
            return 1.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _create_error_response(self, error_message: str, response_time: int) -> Dict:
        """Create standardized error response."""
        return {
            'status': 'error',
            'source': 'sanctions',
            'data': {
                'sanctions_found': [],
                'total_matches': 0,
                'checked_sources': []
            },
            'last_checked': datetime.utcnow().isoformat(),
            'confidence': 0.0,
            'response_time_ms': response_time,
            'error_message': error_message
        }
    
    def get_sanctions_sources_status(self) -> Dict:
        """Check availability of all sanctions data sources."""
        sources = {
            'eu_sanctions': self._test_eu_api(),
            'ofac_sanctions': self._test_ofac_api(),
            'uk_sanctions': self._test_uk_api()
        }
        
        return {
            'sources': sources,
            'total_available': sum(1 for s in sources.values() if s['available']),
            'checked_at': datetime.utcnow().isoformat()
        }
    
    def _test_eu_api(self) -> Dict:
        """Test EU sanctions API availability."""
        try:
            response = self.session.head(self.eu_sanctions_url, timeout=10)
            return {
                'available': response.status_code == 200,
                'response_code': response.status_code,
                'response_time_ms': int(response.elapsed.total_seconds() * 1000)
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'response_time_ms': None
            }
    
    def _test_ofac_api(self) -> Dict:
        """Test OFAC API availability."""
        try:
            response = self.session.get(
                self.ofac_consolidated_url,
                params={'q': 'test', 'size': 1},
                timeout=10
            )
            return {
                'available': response.status_code == 200,
                'response_code': response.status_code,
                'response_time_ms': int(response.elapsed.total_seconds() * 1000)
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'response_time_ms': None
            }
    
    def _test_uk_api(self) -> Dict:
        """Test UK sanctions API availability."""
        try:
            response = self.session.head(self.uk_sanctions_url, timeout=10)
            return {
                'available': response.status_code == 200,
                'response_code': response.status_code,
                'response_time_ms': int(response.elapsed.total_seconds() * 1000)
            }
        except Exception as e:
            return {
                'available': False,
                'error': str(e),
                'response_time_ms': None
            }