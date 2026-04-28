"""
InsolvenzService — German insolvency register checker.

Queries the official German insolvency register at insolvenzbekanntmachungen.de.
Free public service — no API key required.
"""
import time
import logging
from typing import Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_SESSION_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; VATBot/2.0)',
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'de,en;q=0.8',
}

_BASE_URL = 'https://www.insolvenzbekanntmachungen.de'
_SEARCH_URL = f'{_BASE_URL}/ap/suche.jsf'


class InsolvenzService:
    """Check German insolvency register for company proceedings."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(_SESSION_HEADERS)

    def check_insolvency(self, company_name: str, state: Optional[str] = None) -> Dict:
        """
        Query insolvenzbekanntmachungen.de for a company name.

        Returns a standardised response dict compatible with other services.
        """
        start = time.time()
        try:
            results = self._search(company_name, state)
            elapsed = int((time.time() - start) * 1000)

            if results:
                return {
                    'status': 'warning',
                    'source': 'insolvenzbekanntmachungen',
                    'company_name': company_name,
                    'insolvency_found': True,
                    'proceedings': results,
                    'proceedings_count': len(results),
                    'message': f'{len(results)} Insolvenzverfahren gefunden',
                    'response_time_ms': elapsed,
                    'checked_at': datetime.utcnow().isoformat(),
                }

            return {
                'status': 'valid',
                'source': 'insolvenzbekanntmachungen',
                'company_name': company_name,
                'insolvency_found': False,
                'proceedings': [],
                'proceedings_count': 0,
                'message': 'Kein Insolvenzverfahren gefunden',
                'response_time_ms': elapsed,
                'checked_at': datetime.utcnow().isoformat(),
            }

        except requests.Timeout:
            logger.warning(f"InsolvenzService timeout for '{company_name}'")
            return self._error_response(company_name, 'Zeitüberschreitung beim Abruf des Insolvenzregisters')
        except Exception as e:
            logger.error(f"InsolvenzService error for '{company_name}': {e}")
            return self._error_response(company_name, str(e))

    def _search(self, company_name: str, state: Optional[str] = None):
        """POST search form and parse results table."""
        # Step 1: GET the search page to grab the ViewState / session cookies
        get_resp = self.session.get(_SEARCH_URL, timeout=self.timeout)
        get_resp.raise_for_status()

        soup = BeautifulSoup(get_resp.text, 'html.parser')
        view_state = self._extract_view_state(soup)

        # Step 2: POST the search form
        payload = {
            'javax.faces.ViewState': view_state,
            'form': 'form',
            'form:schuldnerName': company_name,
            'form:bundesland': state or '',
            'form:suchen': 'Suchen',
        }

        post_resp = self.session.post(_SEARCH_URL, data=payload, timeout=self.timeout)
        post_resp.raise_for_status()

        return self._parse_results(post_resp.text)

    def _extract_view_state(self, soup: BeautifulSoup) -> str:
        tag = soup.find('input', {'name': 'javax.faces.ViewState'})
        return tag['value'] if tag else ''

    def _parse_results(self, html: str):
        """Parse the results table from the response HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        results = []

        table = soup.find('table', {'class': lambda c: c and 'result' in c.lower()})
        if not table:
            # Try any table with data rows
            table = soup.find('table', id=lambda i: i and 'result' in (i or '').lower())

        if not table:
            return results

        rows = table.find_all('tr')
        headers = [th.get_text(strip=True).lower() for th in (rows[0].find_all('th') if rows else [])]

        for row in rows[1:]:
            cols = [td.get_text(strip=True) for td in row.find_all('td')]
            if not cols:
                continue

            record: Dict = {}
            if headers and len(headers) == len(cols):
                record = dict(zip(headers, cols))
            else:
                # Fallback: store all columns
                record = {f'col_{i}': v for i, v in enumerate(cols)}

            # Normalise common field names
            record.setdefault('raw', ' | '.join(cols))
            results.append(record)

        return results

    @staticmethod
    def _error_response(company_name: str, error_msg: str) -> Dict:
        return {
            'status': 'error',
            'source': 'insolvenzbekanntmachungen',
            'company_name': company_name,
            'insolvency_found': False,
            'proceedings': [],
            'proceedings_count': 0,
            'message': f'Fehler beim Abruf: {error_msg}',
            'checked_at': datetime.utcnow().isoformat(),
        }
