"""
EU Website Compliance Checker — simplified, no browser automation required.
Accessible without registration. Uses requests + BeautifulSoup + Claude AI.
Checks: Impressum, Datenschutz, AGB, Widerrufs, Cookie-Banner.
"""
from __future__ import annotations
import json, re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, request, jsonify, current_app
import anthropic

compliance_checker_bp = Blueprint('compliance_checker', __name__, url_prefix='/compliance-check')

CLAUDE_MODEL = "claude-sonnet-4-6"

LEGAL_PAGES = {
    "Impressum": {
        "keywords": ["impressum", "imprint", "legal notice", "rechtliches", "kontakt / impressum"],
        "url_patterns": ["/impressum", "/imprint", "/legal-notice", "/legal"],
        "law": "§5 TMG / §55 Abs.2 RStV",
        "required": True,
        "required_elements": [
            "Vollständiger Name und Anschrift des Betreibers",
            "Erreichbarkeit: Telefon ODER E-Mail",
            "Umsatzsteuer-ID / Steuer-Nr.",
            "Handelsregistereintrag (bei GmbH / AG / UG / OHG)",
            "Vertretungsberechtigte Person(en)",
        ],
        "prompt_hint": (
            "Check: full legal name, physical street address (P.O. box NOT sufficient), "
            "phone or email, VAT ID, company register number and court."
        ),
    },
    "Datenschutzerklärung": {
        "keywords": ["datenschutz", "datenschutzerklärung", "privacy", "privacy policy", "dsgvo"],
        "url_patterns": ["/datenschutz", "/privacy", "/privacy-policy", "/datenschutzerklaerung"],
        "law": "DSGVO Art. 13/14",
        "required": True,
        "required_elements": [
            "Identität des Verantwortlichen und Kontaktdaten",
            "Zwecke und Rechtsgrundlagen der Datenverarbeitung (Art. 6 DSGVO)",
            "Speicherdauer oder Kriterien",
            "Betroffenenrechte: Auskunft, Berichtigung, Löschung (Art. 15–22 DSGVO)",
            "Recht auf Beschwerde bei der Aufsichtsbehörde",
            "Informationen zu Cookies / Tracking-Diensten",
        ],
        "prompt_hint": (
            "Check every Art. 13/14 DSGVO element: legal basis, data subject rights, "
            "supervisory authority, cookie/tracking. Vague statements are not compliant."
        ),
    },
    "AGB": {
        "keywords": ["agb", "allgemeine geschäftsbedingungen", "terms", "nutzungsbedingungen"],
        "url_patterns": ["/agb", "/terms", "/nutzungsbedingungen", "/terms-of-service"],
        "law": "BGB §305 ff.",
        "required": False,
        "required_elements": [
            "Vertragsgegenstand und Leistungsbeschreibung",
            "Preise und Zahlungsarten",
            "Haftungsausschluss / -beschränkung",
            "Anwendbares Recht und Gerichtsstand",
        ],
        "prompt_hint": "Check for prohibited clauses, clear price info, liability limitations, applicable law.",
    },
    "Widerrufsbelehrung": {
        "keywords": ["widerruf", "widerrufsbelehrung", "widerrufsrecht", "cancellation", "withdrawal"],
        "url_patterns": ["/widerruf", "/cancellation", "/returns", "/widerrufsbelehrung"],
        "law": "§355 BGB / EU-RL 2011/83",
        "required": False,
        "required_elements": [
            "14-tägige Widerrufsfrist",
            "Vollständige Rücksendeadresse",
            "Muster-Widerrufsformular",
            "Rückerstattungsregelung",
        ],
        "prompt_hint": "Check: exact 14-day cooling-off rule, model withdrawal form per Anlage 2 EGBGB.",
    },
}

COOKIE_INDICATORS = [
    "cookiebot", "onetrust", "usercentrics", "ccm19", "borlabs", "klaro",
    "tarteaucitron", "cookie-consent", "cookie_consent", "cookieconsent",
    "cookie-banner", "cookiebanner", "consentmanager", "cookie notice",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; VAT-Compliance-Checker/1.0)"}


def _fetch(url: str, timeout: int = 12) -> tuple[str, BeautifulSoup | None]:
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS, allow_redirects=True)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        return r.text, soup
    except Exception:
        return "", None


def _find_legal_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    links = [(a.get_text(" ", strip=True).lower(), a.get("href", "")) for a in soup.find_all("a", href=True)]
    found: dict[str, str] = {}
    for ptype, cfg in LEGAL_PAGES.items():
        for text, href in links:
            if any(kw in text for kw in cfg["keywords"]):
                found[ptype] = href if href.startswith("http") else urljoin(base_url, href)
                break
        if ptype in found:
            continue
        for text, href in links:
            href_lower = href.lower()
            if any(pat in href_lower for pat in cfg["url_patterns"]):
                found[ptype] = href if href.startswith("http") else urljoin(base_url, href)
                break
    return found


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)[:6000]


def _detect_cookie(raw_html: str) -> dict:
    html_lower = raw_html.lower()
    present = any(ind in html_lower for ind in COOKIE_INDICATORS)
    reject = any(kw in html_lower for kw in ["ablehnen", "reject all", "decline", "nur notwendige", "necessary only"])
    pre_checked = bool(
        re.search(r'(marketing|analytics|tracking)[^>]*checked', html_lower)
    )
    return {"present": present, "reject_option": reject, "pre_checked": pre_checked}


def _parse_json_robust(raw: str) -> dict | None:
    """Extract and parse JSON from Claude output, tolerating markdown fences."""
    # Strip markdown code fences if present
    text = re.sub(r'^```(?:json)?\s*', '', raw.strip(), flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text.strip())
    # Find outermost {...}
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if not m:
        return None
    candidate = m.group()
    # Remove unescaped literal newlines inside JSON string values
    # Replace bare newlines that appear inside string values with \n
    candidate = re.sub(r'(?<!\\)\n', ' ', candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # Last resort: try jsonrepair-style removal of trailing commas
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None


def _claude_analyze(ptype: str, law: str, elements: list, content: str, hint: str, api_key: str) -> dict:
    elems = "; ".join(elements)  # single line avoids newlines in prompt
    prompt = (
        f"Analysiere die '{ptype}'-Seite auf Konformität mit {law}. "
        f"Pflichtangaben: {elems}. Hinweis: {hint}. "
        f"Seiteninhalt (max 5000 Zeichen): {content[:5000]}. "
        'Antworte NUR mit diesem JSON (alle Strings einzeilig, keine Zeilenumbrüche in Werten): '
        '{"found_elements":["..."],"missing_elements":["..."],'
        '"issues":[{"severity":"critical","issue":"text","recommendation":"text"}],'
        '"summary":"2-3 Saetze","compliant":true}'
    )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=900,
            system=(
                "Du bist Experte fuer deutsches IT-Recht und DSGVO. "
                "Antworte AUSSCHLIESSLICH mit einem validen JSON-Objekt. "
                "Alle String-Werte muessen einzeilig sein (keine Zeilenumbrueche innerhalb von Strings)."
            ),
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json_robust(resp.content[0].text)
        if result is not None:
            return result
    except Exception as e:
        current_app.logger.error(f"Compliance Claude error: {e}")
    return {"found_elements": [], "missing_elements": [], "issues": [], "summary": "Analyse fehlgeschlagen.", "compliant": False}


def _calc_score(page_results: dict, cookie: dict) -> tuple[int, str]:
    pts = 100
    imp = page_results.get("Impressum", {})
    if not imp.get("found"):
        pts -= 30
    else:
        pts -= sum(1 for i in imp.get("issues", []) if i.get("severity") == "critical") * 6
        pts -= sum(1 for i in imp.get("issues", []) if i.get("severity") == "warning") * 2
    ds = page_results.get("Datenschutzerklärung", {})
    if not ds.get("found"):
        pts -= 25
    else:
        pts -= sum(1 for i in ds.get("issues", []) if i.get("severity") == "critical") * 5
        pts -= sum(1 for i in ds.get("issues", []) if i.get("severity") == "warning") * 2
    if not cookie.get("present"):
        pts -= 20
    elif not cookie.get("reject_option"):
        pts -= 10
    if cookie.get("pre_checked"):
        pts -= 8
    pts = max(0, min(100, pts))
    grade = "A" if pts >= 90 else "B" if pts >= 75 else "C" if pts >= 60 else "D" if pts >= 40 else "F"
    return pts, grade


@compliance_checker_bp.route('/', methods=['GET'])
def index():
    return render_template('compliance_checker/index.html')


@compliance_checker_bp.route('/check', methods=['POST'])
def check():
    """Run EU compliance check. Returns JSON. No login required."""
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL ist erforderlich'}), 400
    if not url.startswith('http'):
        url = 'https://' + url

    api_key = current_app.config.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'KI-Analyse nicht verfügbar (API-Key fehlt)'}), 500

    # Fetch homepage
    raw_html, soup = _fetch(url)
    if not soup:
        return jsonify({'error': f'Website nicht erreichbar: {url}'}), 400

    # Find legal page links
    legal_links = _find_legal_links(soup, url)

    page_results: dict[str, dict] = {}
    for ptype, cfg in LEGAL_PAGES.items():
        result: dict = {
            'name': ptype,
            'law': cfg['law'],
            'required': cfg['required'],
            'found': ptype in legal_links,
            'url': legal_links.get(ptype, ''),
            'issues': [],
            'summary': '',
            'found_elements': [],
            'missing_elements': [],
        }
        if ptype in legal_links:
            _, page_soup = _fetch(legal_links[ptype])
            if page_soup:
                content = _extract_text(page_soup)
                analysis = _claude_analyze(
                    ptype, cfg['law'], cfg['required_elements'],
                    content, cfg['prompt_hint'], api_key
                )
                result.update({
                    'issues': analysis.get('issues', []),
                    'summary': analysis.get('summary', ''),
                    'found_elements': analysis.get('found_elements', []),
                    'missing_elements': analysis.get('missing_elements', []),
                })
        else:
            if cfg['required']:
                result['issues'] = [{
                    'severity': 'critical',
                    'issue': f'{ptype} nicht gefunden',
                    'recommendation': f'Erstelle eine {ptype}-Seite gemäß {cfg["law"]} und verlinke sie im Footer jeder Seite.',
                }]
        page_results[ptype] = result

    cookie = _detect_cookie(raw_html)
    score, grade = _calc_score(page_results, cookie)

    total_critical = sum(
        sum(1 for i in r['issues'] if i.get('severity') == 'critical')
        for r in page_results.values()
    )
    total_warning = sum(
        sum(1 for i in r['issues'] if i.get('severity') == 'warning')
        for r in page_results.values()
    )

    # Build simplified per-page shape expected by the frontend
    pages: dict = {}
    for ptype, r in page_results.items():
        ok_elements = r.get('found_elements', [])
        issue_texts = [i.get('issue', '') for i in r.get('issues', []) if i.get('severity') in ('critical', 'warning')]
        pages[ptype] = {
            'status': 'found' if r['found'] and not issue_texts else ('partial' if r['found'] else 'not_found'),
            'url': r.get('url', ''),
            'law': r.get('law', ''),
            'summary': r.get('summary', ''),
            'ok_elements': ok_elements,
            'issues': issue_texts,
        }

    ai_summary_parts = []
    if score >= 80:
        ai_summary_parts.append('Die Website erfüllt die wichtigsten rechtlichen Anforderungen.')
    elif score >= 60:
        ai_summary_parts.append('Die Website erfüllt grundlegende Anforderungen, aber es gibt Verbesserungspotenzial.')
    else:
        ai_summary_parts.append('Die Website weist erhebliche Compliance-Lücken auf und sollte dringend überarbeitet werden.')
    if not cookie.get('present'):
        ai_summary_parts.append('Ein Cookie-Banner fehlt — dies ist häufig gemäß ePrivacy-Richtlinie erforderlich.')
    if not page_results.get('Impressum', {}).get('found'):
        ai_summary_parts.append('Das Impressum fehlt — dies ist gemäß §5 TMG zwingend vorgeschrieben.')
    if not page_results.get('Datenschutzerklärung', {}).get('found'):
        ai_summary_parts.append('Die Datenschutzerklärung fehlt — DSGVO Art. 13/14 verpflichten dazu.')

    return jsonify({
        'url': url,
        'score': score,
        'grade': grade,
        'pages': pages,
        'cookie_banner': cookie.get('present', False),
        'cookie': cookie,
        'critical_count': total_critical,
        'warning_count': total_warning,
        'ai_summary': ' '.join(ai_summary_parts),
    })
