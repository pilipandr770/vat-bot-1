"""
Programmatic SEO Routes
Динамічні маршрути для сотень VAT Check сторінок
Кожна сторінка: кейс, FAQ, CTA, Schema.org FAQPage, Related Pages, Breadcrumbs
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

def get_related_pages(current_slug, limit=4):
    """
    Отримує пов'язані сторінки для внутрішнього linкування
    Повертає інші міста для цього типу + інші типи для цього міста
    """
    if current_slug not in _seo_pages:
        return []
    
    current_page = _seo_pages[current_slug]
    business_type = current_page.get('business_type')
    city = current_page.get('city')
    
    related = []
    
    # Додаємо інші міста для цього типу бізнесу
    for slug, page in _seo_pages.items():
        if page.get('business_type') == business_type and page.get('city') != city:
            related.append(page)
            if len(related) >= limit:
                break
    
    # Додаємо інші типи для цього міста, якщо потрібно більше
    if len(related) < limit:
        for slug, page in _seo_pages.items():
            if page.get('city') == city and page.get('business_type') != business_type:
                if page not in related:
                    related.append(page)
                if len(related) >= limit:
                    break
    
    return related[:limit]

def optimize_meta_description(page_data):
    """
    Оптимізує мета-описання з CTA та ключовими словами
    Забезпечує унікальність та привабливість для CTR
    """
    if 'meta_description_optimized' in page_data:
        return page_data['meta_description_optimized']
    
    base_desc = page_data.get('meta_description', '')
    city = page_data.get('city', '')
    business_type = page_data.get('business_type', '')
    
    # Додаємо CTA елемент в кінець
    cta_variants = [
        f"Verify in seconds. Free check.",
        f"Get instant verification report.",
        f"Check instantly - no credit card needed.",
        f"Verify now - completely free.",
    ]
    
    import random
    cta = random.choice(cta_variants)
    
    optimized = f"{base_desc} {cta}"
    
    # Обрізаємо до 160 символів для оптимального відображення у SERP
    if len(optimized) > 160:
        optimized = optimized[:157] + "..."
    
    return optimized

@programmatic_bp.route('/<slug>')
def vat_check_page(slug):
    """
    Динамічна сторінка VAT Check з Related Pages та оптимізованими Meta Descriptions
    URL: /vat-check/gmbh-berlin, /vat-check/freelancer-munich, тощо
    """
    page_data = _seo_pages.get(slug)
    
    if not page_data:
        abort(404)
    
    # Оптимізуємо мета-описання для кращого CTR
    page_data['meta_description_optimized'] = optimize_meta_description(page_data)
    
    # Отримуємо пов'язані сторінки для внутрішнього linкування
    related_pages = get_related_pages(slug, limit=4)
    
    return render_template('programmatic/vat_check_page.html', 
                         page=page_data,
                         related_pages=related_pages,
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

def get_all_pages():
    """Повертає всі сторінки для генерації Sitemap та навігації"""
    return list(_seo_pages.values())

def get_page(slug):
    """Повертає дані окремої сторінки по slug"""
    return _seo_pages.get(slug)