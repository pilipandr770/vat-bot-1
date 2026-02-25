"""
Sitemap Routes
Динамічна генерація XML sitemap з Programmatic SEO сторінками
"""

from flask import Blueprint, current_app
from datetime import datetime
import json
import os

sitemap_bp = Blueprint('sitemap', __name__)

@sitemap_bp.route('/sitemap.xml')
def generate_sitemap():
    """
    Генерує XML sitemap з усіма сторінками:
    - Стандартні сторінки (landing, pricing, about)
    - GEO сторінки (compliance-germany, etc)
    - Programmatic SEO сторінки (vat-check/gmbh-berlin, etc)
    - AI-Search сторінки (answers-for-ai)
    """
    from flask import make_response
    
    urls = []
    
    # 1. Стандартні сторінки
    static_pages = [
        ('/', 'weekly', 1.0),
        ('/pricing', 'weekly', 0.9),
        ('/pentesting-scanner', 'weekly', 0.8),
        ('/legal/agb', 'monthly', 0.5),
        ('/legal/datenschutz', 'monthly', 0.5),
        ('/legal/impressum', 'monthly', 0.5),
    ]
    
    for url, changefreq, priority in static_pages:
        urls.append({
            'loc': f'https://vat-verifizierung.de{url}',
            'lastmod': datetime.now().date().isoformat(),
            'changefreq': changefreq,
            'priority': priority
        })
    
    # 2. GEO сторінки
    geo_pages = [
        ('/about/compliance-germany', 'monthly', 0.8),
        ('/about/why-german-smbs-trust-us', 'monthly', 0.8),
        ('/about/eu-vat-rules', 'monthly', 0.7),
        ('/about/answers-for-ai', 'weekly', 0.9),
    ]
    
    for url, changefreq, priority in geo_pages:
        urls.append({
            'loc': f'https://vat-verifizierung.de{url}',
            'lastmod': datetime.now().date().isoformat(),
            'changefreq': changefreq,
            'priority': priority
        })
    
    # 3. Programmatic SEO сторінки (з JSON файлу)
    try:
        # programmatic_seo_pages.json lives at the project root (same as programmatic/routes.py expects)
        json_path = os.path.join(os.path.dirname(__file__), '..', 'programmatic_seo_pages.json')
        json_path = os.path.normpath(json_path)
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                pages = json.load(f)
                for page in pages:
                    urls.append({
                        'loc': f'https://vat-verifizierung.de{page["url"]}',
                        'lastmod': datetime.now().date().isoformat(),
                        'changefreq': 'monthly',
                        'priority': 0.7
                    })
    except Exception as e:
        current_app.logger.warning(f'Could not load programmatic SEO pages for sitemap: {e}')

    # 4. Blog posts (from database — always fresh lastmod)
    try:
        from crm.models import BlogPost
        blog_posts = (BlogPost.query
                      .filter_by(is_published=True)
                      .order_by(BlogPost.published_at.desc())
                      .limit(500)
                      .all())
        # Blog index page
        urls.append({
            'loc': 'https://vat-verifizierung.de/blog/',
            'lastmod': blog_posts[0].published_at.date().isoformat() if blog_posts else datetime.now().date().isoformat(),
            'changefreq': 'daily',
            'priority': 0.9
        })
        for post in blog_posts:
            urls.append({
                'loc': f'https://vat-verifizierung.de/blog/{post.slug}',
                'lastmod': post.published_at.date().isoformat() if post.published_at else datetime.now().date().isoformat(),
                'changefreq': 'monthly',
                'priority': 0.75
            })
    except Exception as e:
        current_app.logger.warning(f'Could not load blog posts for sitemap: {e}')
    
    # Генеруємо XML
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
    
    for url in urls:
        xml += '  <url>\n'
        xml += f'    <loc>{url["loc"]}</loc>\n'
        xml += f'    <lastmod>{url["lastmod"]}</lastmod>\n'
        xml += f'    <changefreq>{url["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{url["priority"]}</priority>\n'
        # add hreflang alternates (German + default)
        xml += f'    <xhtml:link rel="alternate" hreflang="de-DE" href="{url["loc"]}"/>\n'
        xml += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{url["loc"]}"/>\n'
        xml += '  </url>\n'
    
    xml += '</urlset>'
    
    response = make_response(xml)
    response.headers['Content-Type'] = 'application/xml'
    return response
