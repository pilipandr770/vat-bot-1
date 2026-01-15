#!/usr/bin/env python3
"""
Generate sitemap.xml for VAT Verifizierung with 50+ pages
Includes: GEO pages, business type pages, AI pages, guides, and main pages
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# Define all page groups
PAGES = {
    # Core pages - Daily updates
    "core": {
        "priority": 1.0,
        "changefreq": "daily",
        "pages": [
            "/",
            "/vat-check/",
            "/ai/",
            "/faq/",
            "/about/",
            "/about/answers-for-ai",
        ]
    },
    
    # GEO pages - Weekly updates (15 major German cities)
    "geo": {
        "priority": 0.85,
        "changefreq": "weekly",
        "pages": [
            "/vat-check-berlin/",
            "/vat-check-munich/",
            "/vat-check-hamburg/",
            "/vat-check-cologne/",
            "/vat-check-frankfurt/",
            "/vat-check-stuttgart/",
            "/vat-check-dusseldorf/",
            "/vat-check-dortmund/",
            "/vat-check-essen/",
            "/vat-check-leipzig/",
            "/vat-check-nuremberg/",
            "/vat-check-hanover/",
            "/vat-check-bremen/",
            "/vat-check-dresden/",
            "/vat-check-duisburg/",
        ]
    },
    
    # Business type pages - Weekly updates (8 industries)
    "business": {
        "priority": 0.85,
        "changefreq": "weekly",
        "pages": [
            "/vat-check-for-ecommerce/",
            "/vat-check-for-b2b-suppliers/",
            "/vat-check-for-freelancers/",
            "/vat-check-for-import-export/",
            "/vat-check-for-saas/",
            "/vat-check-for-manufacturing/",
            "/vat-check-for-startups/",
            "/vat-check-for-agencies/",
        ]
    },
    
    # Guide & resources - Monthly updates
    "resources": {
        "priority": 0.75,
        "changefreq": "monthly",
        "pages": [
            "/guide/vat-verification-germany/",
            "/guide/eu-vat-number-validation/",
            "/guide/vat-compliance-sme/",
            "/resources/vat-database/",
            "/guide/fraud-prevention/",
            "/guide/partner-verification/",
        ]
    },
    
    # Legal & info pages - Yearly updates
    "legal": {
        "priority": 0.5,
        "changefreq": "yearly",
        "pages": [
            "/legal/imprint/",
            "/legal/privacy/",
            "/legal/terms/",
            "/legal/gdpr/",
        ]
    }
}

def create_sitemap():
    """Create XML sitemap with all pages"""
    root = ET.Element("urlset")
    root.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root.set("xmlns:news", "http://www.google.com/schemas/sitemap-news/0.9")
    root.set("xmlns:mobile", "http://www.google.com/schemas/sitemap-mobile/1.0")
    
    now = datetime.utcnow().isoformat() + "Z"
    base_url = "https://vat-verifizierung.de"
    
    total_pages = 0
    
    # Add all pages
    for group_name, group_data in PAGES.items():
        priority = group_data["priority"]
        changefreq = group_data["changefreq"]
        
        for page in group_data["pages"]:
            url_element = ET.SubElement(root, "url")
            
            loc = ET.SubElement(url_element, "loc")
            loc.text = f"{base_url}{page}"
            
            lastmod = ET.SubElement(url_element, "lastmod")
            lastmod.text = now
            
            changef = ET.SubElement(url_element, "changefreq")
            changef.text = changefreq
            
            prio = ET.SubElement(url_element, "priority")
            prio.text = str(priority)
            
            total_pages += 1
    
    # Pretty print
    tree = ET.ElementTree(root)
    tree.write(
        "public/sitemap.xml",
        encoding="utf-8",
        xml_declaration=True
    )
    
    print(f"✅ Sitemap created: public/sitemap.xml")
    print(f"📊 Total URLs: {total_pages}")
    print(f"📅 Generated: {now}")
    
    return total_pages

if __name__ == "__main__":
    total = create_sitemap()
    print(f"\n✨ Sitemap ready for submission to:")
    print(f"   - Google Search Console")
    print(f"   - Bing Webmaster Tools")
    print(f"   - robots.txt (Sitemap: https://vat-verifizierung.de/sitemap.xml)")
