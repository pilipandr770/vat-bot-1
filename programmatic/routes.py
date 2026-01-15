"""
Programmatic SEO Routes
Динамічні маршрути для сотень VAT Check сторінок
Кожна сторінка: кейс, FAQ, CTA, Schema.org FAQPage
"""

from flask import Blueprint, render_template, abort
import json
import os

programmatic_bp = Blueprint('programmatic', __name__, url_prefix='/vat-check')

# Завантажуємо дані при ініціалізації
def load_seo_pages():
    """Завантажує дані Programmatic SEO сторінок"""
    json_path = os.path.join(os.path.dirname(__file__), '..', 'programmatic_seo_pages.json')
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            pages = json.load(f)
            # Індексуємо за slug для швидкого доступу
            return {page['slug']: page for page in pages}
    except Exception as e:
        print(f"Warning: Could not load SEO pages: {e}")
        return {}

# Глобальна змінна для зберігання сторінок
_seo_pages = load_seo_pages()

@programmatic_bp.route('/<slug>')
def vat_check_page(slug):
    """
    Динамічна сторінка VAT Check
    URL: /vat-check/gmbh-berlin, /vat-check/freelancer-munich, тощо
    """
    page_data = _seo_pages.get(slug)
    
    if not page_data:
        abort(404)
    
    return render_template('programmatic/vat_check_page.html', 
                         page=page_data,
                         business_type=slug.split('-')[0],
                         city=slug.split('-')[1] if '-' in slug else 'default')

@programmatic_bp.route('/sitemap')
def programmatic_sitemap():
    """
    Посилання на всі Programmatic SEO сторінки (для Sitemap та навігації)
    JSON формат для легкої індексації
    """
    return {
        'total_pages': len(_seo_pages),
        'pages': [
            {
                'url': page['url'],
                'title': page['title'],
                'keyword': page['main_keyword']
            }
            for page in _seo_pages.values()
        ]
    }

@programmatic_bp.before_app_serving
def reload_seo_pages():
    """
    Перезавантажує дані на старт додатка
    Дозволяє оновлювати сторінки без перезапуску
    """
    global _seo_pages
    _seo_pages = load_seo_pages()

def get_all_pages():
    """Повертає усі сторінки (для Sitemap та індексації)"""
    return _seo_pages.values()

def get_page(slug):
    """Повертає одну сторінку за slug"""
    return _seo_pages.get(slug)
