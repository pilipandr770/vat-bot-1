"""
Link Scanner - URL Threat Detection API
Проверка ссылок на фишинг, вредоносное ПО и другие угрозы.
"""
import os
import re
import hashlib
import logging
from urllib.parse import urlparse, parse_qs
from datetime import datetime

import requests
import tldextract
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from . import link_scanner

logger = logging.getLogger(__name__)

# Известные подозрительные TLD
SUSPICIOUS_TLDS = {
    'tk', 'ml', 'ga', 'cf', 'gq',  # Бесплатные домены
    'xyz', 'top', 'work', 'click', 'link', 'info',
    'online', 'site', 'website', 'space', 'pw', 'cc',
    'su', 'ws', 'biz', 'icu', 'buzz', 'rest'
}

# Сервисы сокращения ссылок
URL_SHORTENERS = {
    'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly',
    'is.gd', 'buff.ly', 'adf.ly', 'bl.ink', 'lnkd.in',
    'shorte.st', 'clck.ru', 'rebrand.ly', 'cutt.ly', 'shorturl.at'
}

# Фишинговые ключевые слова в URL
PHISHING_KEYWORDS = [
    'login', 'signin', 'verify', 'update', 'secure', 'account',
    'banking', 'paypal', 'ebay', 'amazon', 'microsoft', 'apple',
    'google', 'facebook', 'instagram', 'netflix', 'password',
    'confirm', 'suspend', 'unusual', 'alert', 'security',
    'wallet', 'crypto', 'bitcoin', 'ethereum'
]

# Белый список популярных доменов
TRUSTED_DOMAINS = {
    'google.com', 'google.de', 'youtube.com', 'facebook.com',
    'amazon.com', 'amazon.de', 'microsoft.com', 'apple.com',
    'github.com', 'linkedin.com', 'twitter.com', 'instagram.com',
    'wikipedia.org', 'reddit.com', 'netflix.com', 'paypal.com',
    'ebay.com', 'ebay.de', 'dropbox.com', 'zoom.us'
}


@link_scanner.route('/')
@login_required
def scan_page():
    """Страница Link Scanner."""
    return render_template('link_scanner/scan.html')


@link_scanner.route('/api/scan', methods=['POST'])
@login_required
def scan_url():
    """API endpoint для сканирования URL."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'Keine URL angegeben'
            }), 400

        url = data['url'].strip()

        # Валидация URL
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL darf nicht leer sein'
            }), 400

        # Добавляем схему если отсутствует
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Проверяем формат URL
        try:
            parsed = urlparse(url)
            if not parsed.netloc:
                raise ValueError("Invalid URL")
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Ungültiges URL-Format'
            }), 400

        # Выполняем комплексную проверку
        result = analyze_url(url)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Link scan error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Fehler bei der Analyse: {str(e)}'
        }), 500


@link_scanner.route('/api/batch-scan', methods=['POST'])
@login_required
def batch_scan_urls():
    """API endpoint для пакетного сканирования нескольких URL."""
    try:
        data = request.get_json()
        urls = data.get('urls', [])

        if not urls or not isinstance(urls, list):
            return jsonify({
                'success': False,
                'error': 'Keine URLs angegeben'
            }), 400

        if len(urls) > 20:
            return jsonify({
                'success': False,
                'error': 'Maximal 20 URLs pro Anfrage'
            }), 400

        results = []
        for url in urls:
            url = url.strip()
            if not url:
                continue

            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            try:
                result = analyze_url(url)
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'url': url,
                    'error': str(e)
                })

        # Общая статистика
        safe_count = sum(1 for r in results if r.get('verdict') == 'safe')
        suspicious_count = sum(1 for r in results if r.get('verdict') == 'suspicious')
        malicious_count = sum(1 for r in results if r.get('verdict') == 'malicious')

        return jsonify({
            'success': True,
            'total': len(results),
            'summary': {
                'safe': safe_count,
                'suspicious': suspicious_count,
                'malicious': malicious_count
            },
            'results': results
        })

    except Exception as e:
        logger.error(f"Batch link scan error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def analyze_url(url: str) -> dict:
    """
    Комплексный анализ URL на угрозы.
    """
    parsed = urlparse(url)
    extracted = tldextract.extract(url)

    domain = f"{extracted.domain}.{extracted.suffix}"
    full_domain = parsed.netloc.lower()

    result = {
        'success': True,
        'url': url,
        'domain': domain,
        'full_domain': full_domain,
        'scheme': parsed.scheme,
        'path': parsed.path,
        'scan_time': datetime.utcnow().isoformat(),
        'checks': {},
        'score': 0,
        'verdict': 'safe',
        'threats': [],
        'recommendations': []
    }

    # 1. Проверка схемы (HTTP vs HTTPS)
    result['checks']['ssl'] = check_ssl(parsed)

    # 2. Локальные эвристики
    result['checks']['heuristics'] = check_heuristics(url, parsed, extracted, domain)

    # 3. VirusTotal API (если настроен)
    result['checks']['virustotal'] = check_virustotal(url)

    # 4. Google Safe Browsing (если настроен)
    result['checks']['safe_browsing'] = check_safe_browsing(url)

    # 5. Проверка доступности
    result['checks']['accessibility'] = check_url_accessibility(url)

    # Вычисляем итоговый score и verdict
    calculate_final_verdict(result)

    return result


def check_ssl(parsed) -> dict:
    """Проверка использования HTTPS."""
    if parsed.scheme == 'https':
        return {
            'status': 'safe',
            'message': 'Sichere HTTPS-Verbindung',
            'score': 0
        }
    else:
        return {
            'status': 'warning',
            'message': 'Unsichere HTTP-Verbindung (kein SSL)',
            'score': 15
        }


def check_heuristics(url: str, parsed, extracted, domain: str) -> dict:
    """Локальный эвристический анализ URL."""
    issues = []
    score = 0

    # 1. Проверка TLD
    if extracted.suffix in SUSPICIOUS_TLDS:
        issues.append(f'Verdächtige TLD: .{extracted.suffix}')
        score += 20

    # 2. Проверка сокращателей ссылок
    if any(shortener in parsed.netloc.lower() for shortener in URL_SHORTENERS):
        issues.append('URL-Shortener erkannt - Ziel unbekannt')
        score += 25

    # 3. Проверка на фишинговые ключевые слова
    url_lower = url.lower()
    found_keywords = [kw for kw in PHISHING_KEYWORDS if kw in url_lower]
    if found_keywords and domain not in TRUSTED_DOMAINS:
        issues.append(f'Verdächtige Schlüsselwörter: {", ".join(found_keywords[:3])}')
        score += min(len(found_keywords) * 10, 30)

    # 4. Проверка IP-адреса вместо домена
    ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ip_pattern, extracted.domain):
        issues.append('IP-Adresse statt Domainname verwendet')
        score += 30

    # 5. Проверка подозрительных поддоменов (typosquatting)
    if extracted.subdomain:
        suspicious_subdomains = ['secure', 'login', 'account', 'update', 'verify', 'support']
        for sus in suspicious_subdomains:
            if sus in extracted.subdomain.lower():
                issues.append(f'Verdächtige Subdomain: {extracted.subdomain}')
                score += 20
                break

    # 6. Проверка длины URL (фишинговые часто очень длинные)
    if len(url) > 200:
        issues.append('Ungewöhnlich lange URL')
        score += 10

    # 7. Проверка специальных символов
    special_chars = url.count('@') + url.count('%') + url.count('&') * 0.5
    if special_chars > 5:
        issues.append('Viele Sonderzeichen in der URL')
        score += 15

    # 8. Проверка на двойные расширения в пути
    if re.search(r'\.\w{2,4}\.\w{2,4}$', parsed.path):
        issues.append('Doppelte Dateierweiterung erkannt')
        score += 25

    # 9. Проверка доверенных доменов
    if domain in TRUSTED_DOMAINS:
        # Понижаем score для доверенных доменов
        score = max(0, score - 30)

    status = 'safe'
    if score >= 50:
        status = 'danger'
    elif score >= 20:
        status = 'warning'

    return {
        'status': status,
        'issues': issues,
        'score': score,
        'trusted_domain': domain in TRUSTED_DOMAINS
    }


def check_virustotal(url: str) -> dict:
    """Проверка URL через VirusTotal API."""
    api_key = current_app.config.get('VIRUSTOTAL_API_KEY')

    if not api_key:
        return {
            'status': 'unavailable',
            'message': 'VirusTotal API nicht konfiguriert',
            'score': 0
        }

    try:
        # Создаём URL ID для VirusTotal (base64 без padding)
        import base64
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip('=')

        headers = {'x-apikey': api_key}

        # Сначала проверяем есть ли уже результат
        response = requests.get(
            f'https://www.virustotal.com/api/v3/urls/{url_id}',
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            stats = data['data']['attributes']['last_analysis_stats']
            malicious = stats.get('malicious', 0)
            suspicious = stats.get('suspicious', 0)
            total = sum(stats.values())

            score = 0
            if malicious > 0:
                score = min(malicious * 10, 50)
            elif suspicious > 0:
                score = min(suspicious * 5, 25)

            status = 'safe'
            if malicious > 3:
                status = 'danger'
            elif malicious > 0 or suspicious > 2:
                status = 'warning'

            return {
                'status': status,
                'malicious': malicious,
                'suspicious': suspicious,
                'total_engines': total,
                'score': score,
                'link': f'https://www.virustotal.com/gui/url/{url_id}'
            }

        elif response.status_code == 404:
            # URL не найден, отправляем на сканирование
            scan_response = requests.post(
                'https://www.virustotal.com/api/v3/urls',
                headers=headers,
                data={'url': url},
                timeout=10
            )

            if scan_response.status_code == 200:
                return {
                    'status': 'pending',
                    'message': 'URL zur Analyse eingereicht',
                    'score': 0
                }

        return {
            'status': 'error',
            'message': f'API Fehler: {response.status_code}',
            'score': 0
        }

    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': 'VirusTotal Timeout',
            'score': 0
        }
    except Exception as e:
        logger.warning(f"VirusTotal check failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'score': 0
        }


def check_safe_browsing(url: str) -> dict:
    """Проверка через Google Safe Browsing API."""
    api_key = current_app.config.get('GOOGLE_SAFE_BROWSING_API_KEY')

    if not api_key:
        return {
            'status': 'unavailable',
            'message': 'Google Safe Browsing nicht konfiguriert',
            'score': 0
        }

    try:
        endpoint = f'https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}'

        payload = {
            'client': {
                'clientId': 'vat-verification-system',
                'clientVersion': '1.0.0'
            },
            'threatInfo': {
                'threatTypes': [
                    'MALWARE',
                    'SOCIAL_ENGINEERING',
                    'UNWANTED_SOFTWARE',
                    'POTENTIALLY_HARMFUL_APPLICATION'
                ],
                'platformTypes': ['ANY_PLATFORM'],
                'threatEntryTypes': ['URL'],
                'threatEntries': [{'url': url}]
            }
        }

        response = requests.post(endpoint, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])

            if matches:
                threats = [m.get('threatType', 'UNKNOWN') for m in matches]
                return {
                    'status': 'danger',
                    'threats': threats,
                    'message': f'Google erkennt Bedrohungen: {", ".join(threats)}',
                    'score': 50
                }
            else:
                return {
                    'status': 'safe',
                    'message': 'Keine Bedrohungen von Google erkannt',
                    'score': 0
                }

        return {
            'status': 'error',
            'message': f'API Fehler: {response.status_code}',
            'score': 0
        }

    except Exception as e:
        logger.warning(f"Safe Browsing check failed: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'score': 0
        }


def check_url_accessibility(url: str) -> dict:
    """Проверка доступности URL и анализ ответа."""
    try:
        response = requests.head(
            url,
            timeout=5,
            allow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LinkScanner/1.0)'}
        )

        redirects = len(response.history)
        final_url = response.url

        result = {
            'status': 'safe',
            'status_code': response.status_code,
            'redirects': redirects,
            'final_url': final_url if final_url != url else None,
            'score': 0
        }

        # Проверка редиректов
        if redirects > 3:
            result['status'] = 'warning'
            result['message'] = f'{redirects} Weiterleitungen erkannt'
            result['score'] = 15

        # Проверка изменения домена при редиректе
        if final_url and final_url != url:
            original_domain = tldextract.extract(url).registered_domain
            final_domain = tldextract.extract(final_url).registered_domain
            if original_domain != final_domain:
                result['status'] = 'warning'
                result['message'] = f'Weiterleitung zu anderer Domain: {final_domain}'
                result['score'] = 20

        return result

    except requests.exceptions.SSLError:
        return {
            'status': 'warning',
            'message': 'SSL-Zertifikatfehler',
            'score': 25
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'warning',
            'message': 'Verbindung fehlgeschlagen',
            'score': 10
        }
    except requests.exceptions.Timeout:
        return {
            'status': 'warning',
            'message': 'Timeout - Server antwortet nicht',
            'score': 5
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'score': 0
        }


def calculate_final_verdict(result: dict):
    """Вычисление итогового вердикта на основе всех проверок."""
    total_score = 0
    threats = []
    recommendations = []

    for check_name, check_data in result['checks'].items():
        if isinstance(check_data, dict):
            total_score += check_data.get('score', 0)

            # Собираем угрозы
            if check_data.get('status') == 'danger':
                if 'message' in check_data:
                    threats.append(check_data['message'])
                if 'threats' in check_data:
                    threats.extend(check_data['threats'])
                if 'issues' in check_data:
                    threats.extend(check_data['issues'])

    # Нормализуем score (max 100)
    result['score'] = min(total_score, 100)

    # Определяем verdict
    if result['score'] >= 50:
        result['verdict'] = 'malicious'
        recommendations.append('Diese URL sollte NICHT geöffnet werden')
        recommendations.append('Melden Sie den Link als Phishing/Betrug')
    elif result['score'] >= 25:
        result['verdict'] = 'suspicious'
        recommendations.append('Vorsicht beim Öffnen dieser URL')
        recommendations.append('Überprüfen Sie die Domain sorgfältig')
    else:
        result['verdict'] = 'safe'
        recommendations.append('URL scheint sicher zu sein')

    # Рекомендации по SSL
    if result['checks'].get('ssl', {}).get('status') == 'warning':
        recommendations.append('Geben Sie keine sensiblen Daten auf HTTP-Seiten ein')

    result['threats'] = threats
    result['recommendations'] = recommendations
