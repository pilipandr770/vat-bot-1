#!/usr/bin/env python3
"""
Auto-generate GEO and Business Type pages for VAT Verifizierung
Focus: Fraud prevention, partner verification, business protection
"""

import os
import json
from pathlib import Path

# German cities for VAT verification
CITIES = {
    "berlin": {"name": "Berlin", "region": "Berlin", "population": "3.6M"},
    "munich": {"name": "Munich", "region": "Bavaria", "population": "1.5M"},
    "hamburg": {"name": "Hamburg", "region": "Hamburg", "population": "1.9M"},
    "cologne": {"name": "Cologne", "region": "North Rhine-Westphalia", "population": "1.1M"},
    "frankfurt": {"name": "Frankfurt", "region": "Hesse", "population": "0.75M"},
    "stuttgart": {"name": "Stuttgart", "region": "Baden-Württemberg", "population": "0.63M"},
    "dusseldorf": {"name": "Düsseldorf", "region": "North Rhine-Westphalia", "population": "0.62M"},
    "dortmund": {"name": "Dortmund", "region": "North Rhine-Westphalia", "population": "0.59M"},
    "essen": {"name": "Essen", "region": "North Rhine-Westphalia", "population": "0.58M"},
    "leipzig": {"name": "Leipzig", "region": "Saxony", "population": "0.61M"},
    "nuremberg": {"name": "Nuremberg", "region": "Bavaria", "population": "0.52M"},
    "hanover": {"name": "Hanover", "region": "Lower Saxony", "population": "0.54M"},
    "bremen": {"name": "Bremen", "region": "Bremen", "population": "0.58M"},
    "dresden": {"name": "Dresden", "region": "Saxony", "population": "0.55M"},
    "duisburg": {"name": "Duisburg", "region": "North Rhine-Westphalia", "population": "0.49M"},
}

# Business types / use cases
BUSINESS_TYPES = {
    "ecommerce": {
        "name": "E-Commerce & Online Shops",
        "title": "VAT Verification & Fraud Prevention for E-Commerce",
        "desc": "Protect your online store from supplier fraud, fake sellers, and invoice scams. Verify business partners in real-time before importing goods or partnering with dropshippers."
    },
    "b2b-suppliers": {
        "name": "B2B Suppliers & Wholesalers",
        "title": "Partner Due Diligence for B2B Suppliers",
        "desc": "Screen wholesale suppliers and business partners for legitimacy, fraud history, and VAT compliance. Prevent supply chain fraud and counterfeit goods."
    },
    "freelancers": {
        "name": "Freelancers & Consultants",
        "title": "Business Verification for Freelancers",
        "desc": "Verify client legitimacy before accepting contracts. Check if clients are legitimate businesses to prevent payment fraud and invoice scams."
    },
    "import-export": {
        "name": "Import/Export Businesses",
        "title": "Customs & VAT Compliance for International Trade",
        "desc": "Verify trading partners across EU borders. Ensure compliance with Intrastat reporting, reverse charge rules, and prevent carousel fraud schemes."
    },
    "saas": {
        "name": "SaaS & Digital Services",
        "title": "Customer Verification & Fraud Prevention for SaaS",
        "desc": "Screen new B2B customers for legitimacy and payment risk. Prevent fraud in digital service contracts and subscription businesses."
    },
    "manufacturing": {
        "name": "Manufacturing & Industry",
        "title": "Supply Chain Verification for Manufacturers",
        "desc": "Verify raw material suppliers and component manufacturers. Protect against supplier fraud and ensure business continuity."
    },
    "startups": {
        "name": "Startups & Growth Companies",
        "title": "Risk Assessment for Startup Partnerships",
        "desc": "Conduct due diligence on early-stage investors, partners, and clients. Verify business legitimacy to secure funding and partnerships."
    },
    "agencies": {
        "name": "Marketing & Digital Agencies",
        "title": "Client Verification for Agencies",
        "desc": "Verify client legitimacy before starting projects. Prevent fraud in client contracts and ensure payment security."
    }
}

GEO_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VAT Verification & Fraud Prevention in {city_name} | vat-verifizierung.de</title>
    <meta name="description" content="Verify business partners and prevent fraud in {city_name}, {region}. Real-time VAT validation, partner due diligence, and anti-scam protection for {city_name} businesses.">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <meta name="geo.placename" content="{city_name}">
    <meta name="geo.region" content="DE">
    <link rel="canonical" href="https://vat-verifizierung.de/vat-check-{city_slug}/">
    
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "LocalBusiness",
      "name": "VAT Verification Service {city_name}",
      "image": "https://vat-verifizierung.de/logo.png",
      "description": "Professional VAT verification, fraud prevention, and partner due diligence for businesses in {city_name}",
      "url": "https://vat-verifizierung.de/vat-check-{city_slug}/",
      "areaServed": "{city_name}, {region}, Germany",
      "serviceType": "Business Verification, Fraud Prevention, Partner Due Diligence",
      "telephone": "+49...",
      "priceRange": "€€"
    }}
    </script>

    <meta property="og:title" content="VAT Verification & Fraud Prevention in {city_name}">
    <meta property="og:url" content="https://vat-verifizierung.de/vat-check-{city_slug}/">
    <meta property="og:type" content="website">

    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ font-size: 2.5em; margin-bottom: 10px; color: #0066cc; }}
        .subtitle {{ font-size: 1.1em; color: #666; margin-bottom: 40px; }}
        .benefits {{ background: #f0f8ff; padding: 20px; border-radius: 8px; margin: 30px 0; }}
        .benefit-item {{ margin: 15px 0; }}
        .benefit-item strong {{ color: #0066cc; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>VAT Verification & Fraud Prevention in {city_name}</h1>
        <p class="subtitle">Protect your business with real-time partner verification and anti-scam checks</p>

        <p>
            {city_name} ({city_population}) is a major business hub in {region}. Whether you operate a B2B supplier network, e-commerce platform, or SaaS service in {city_name}, verifying business partners is critical to prevent fraud and protect your bottom line.
        </p>

        <h2 style="margin-top: 30px; color: #0066cc;">Why {city_name} Businesses Need VAT Verification</h2>
        
        <div class="benefits">
            <div class="benefit-item">
                <strong>Prevent Supplier Fraud:</strong> Verify all suppliers and wholesalers against official databases before paying invoices. Avoid fake businesses and carousel fraud schemes.
            </div>
            <div class="benefit-item">
                <strong>Partner Due Diligence:</strong> Screen potential business partners, investors, and clients for legitimacy. Reduce fraud risk before signing contracts.
            </div>
            <div class="benefit-item">
                <strong>VAT Compliance:</strong> Ensure all trading partners are legitimate, registered VAT businesses. Protect yourself from reverse charge obligations and fraudulent invoices.
            </div>
            <div class="benefit-item">
                <strong>Payment Security:</strong> Verify customer legitimacy before extending credit or accepting large orders. Reduce bad debt and payment fraud.
            </div>
            <div class="benefit-item">
                <strong>Fast Risk Assessment:</strong> Real-time VAT validation, business history checks, and fraud indicators—all in seconds.
            </div>
        </div>

        <h2 style="margin-top: 30px; color: #0066cc;">VAT Verification for {city_name} Businesses</h2>
        <p>
            Our VAT Check tool provides {city_name} businesses with instant verification of German (Umsatzsteuer-ID) and EU VAT numbers. Cross-reference against official VIES database and identify fraud red flags before they cost you money.
        </p>

        <p>
            Common use cases in {city_name}:
        </p>
        <ul style="margin-left: 20px; margin-top: 15px;">
            <li>E-commerce platform owner verifying supplier legitimacy</li>
            <li>Manufacturing company screening raw material suppliers</li>
            <li>Freelancer/Agency verifying client legitimacy before projects</li>
            <li>B2B distributor conducting partner due diligence</li>
            <li>Import/Export business ensuring compliance with EU regulations</li>
        </ul>

        <h2 style="margin-top: 30px; color: #0066cc;">How VAT Verification Works</h2>
        <ol style="margin-left: 20px; margin-top: 15px;">
            <li><strong>Enter VAT Number:</strong> Input the business VAT number (format: DE + 9 digits)</li>
            <li><strong>Instant Validation:</strong> Cross-check against German tax authority (Bundeszentralamt für Steuern) and EU VIES database</li>
            <li><strong>View Results:</strong> See business name, address, registration status, and fraud indicators</li>
            <li><strong>Make Decision:</strong> Proceed with partnership or conduct deeper due diligence</li>
        </ol>

        <h2 style="margin-top: 30px; color: #0066cc;">Fraud Red Flags to Watch</h2>
        <ul style="margin-left: 20px; margin-top: 15px;">
            <li>Mismatched VAT numbers or business names</li>
            <li>Newly registered companies with high-value offers</li>
            <li>Unusual business models or trading patterns</li>
            <li>Requests for payment outside EU or via unusual channels</li>
            <li>Pressure for immediate decisions or large commitments</li>
        </ul>

        <p style="margin-top: 30px; font-style: italic; color: #666;">
            Protect your {city_name} business from fraud. Verify business partners today with VAT Verifizierung.
        </p>

    </div>
</body>
</html>
"""

BUSINESS_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | vat-verifizierung.de</title>
    <meta name="description" content="{desc}">
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">
    <link rel="canonical" href="https://vat-verifizierung.de/vat-check-{slug}/">
    
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "{title}",
      "description": "{desc}",
      "url": "https://vat-verifizierung.de/vat-check-{slug}/",
      "applicationCategory": "BusinessApplication",
      "operatingSystem": "Web-based"
    }}
    </script>

    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{desc}">
    <meta property="og:url" content="https://vat-verifizierung.de/vat-check-{slug}/">
    <meta property="og:type" content="website">

    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 40px 20px; }}
        h1 {{ font-size: 2.5em; margin-bottom: 10px; color: #0066cc; }}
        .subtitle {{ font-size: 1.1em; color: #666; margin-bottom: 40px; }}
        .solution-box {{ background: #f0f8ff; padding: 20px; border-radius: 8px; margin: 30px 0; }}
        .solution-item {{ margin: 15px 0; }}
        .solution-item strong {{ color: #0066cc; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="subtitle">{desc}</p>

        <p>
            Protect your {business_type} business from fraud and payment risk. Verify all business partners, suppliers, and customers in real-time using VAT Verifizierung's fraud detection platform.
        </p>

        <h2 style="margin-top: 30px; color: #0066cc;">Why {business_type} Need Fraud Prevention</h2>

        <div class="solution-box">
            <div class="solution-item">
                <strong>Reduce Fraud Risk:</strong> Screen suppliers, customers, and partners for legitimacy. Prevent invoice fraud, non-payment scams, and carousel fraud schemes.
            </div>
            <div class="solution-item">
                <strong>Real-Time Verification:</strong> Instant VAT number validation against official databases. Get results in seconds, not days.
            </div>
            <div class="solution-item">
                <strong>Due Diligence Automation:</strong> Automated business verification checks save time and reduce manual review workload.
            </div>
            <div class="solution-item">
                <strong>Compliance Protection:</strong> Ensure all business partners are VAT-registered and legitimate. Reduce audit risk.
            </div>
            <div class="solution-item">
                <strong>Cost Savings:</strong> Prevent bad debt, fraud losses, and payment defaults. Every verification could save thousands.
            </div>
        </div>

        <h2 style="margin-top: 30px; color: #0066cc;">How {business_type} Use VAT Verification</h2>
        <p>
            {use_case_description}
        </p>

        <h2 style="margin-top: 30px; color: #0066cc;">Common Fraud Scenarios in {business_type}</h2>
        <ul style="margin-left: 20px; margin-top: 15px;">
            <li>Fake supplier invoices from non-existent VAT numbers</li>
            <li>Carousel fraud schemes (buy-sell-buy VAT manipulation)</li>
            <li>Payment fraud from illegitimate customers</li>
            <li>Contract fraud with non-registered businesses</li>
            <li>Invoice manipulation and duplicate billing schemes</li>
        </ul>

        <h2 style="margin-top: 30px; color: #0066cc;">Start Verifying Today</h2>
        <p>
            Protect your {business_type} with real-time fraud prevention. Verify any German or EU VAT number in seconds. Get business details, compliance status, and fraud risk assessment instantly.
        </p>

    </div>
</body>
</html>
"""

def create_geo_pages():
    """Generate GEO-specific pages for each German city"""
    geo_dir = Path("public/vat-check")
    geo_dir.mkdir(parents=True, exist_ok=True)
    
    for slug, city_info in CITIES.items():
        filename = geo_dir / f"{slug}.html"
        content = GEO_TEMPLATE.format(
            city_name=city_info["name"],
            city_slug=slug,
            region=city_info["region"],
            city_population=city_info["population"]
        )
        filename.write_text(content, encoding="utf-8")
        print(f"✅ Created: public/vat-check/{slug}.html")

def create_business_pages():
    """Generate business type-specific pages"""
    biz_dir = Path("public/vat-check")
    biz_dir.mkdir(parents=True, exist_ok=True)
    
    use_case_descriptions = {
        "ecommerce": "E-commerce platforms need to verify suppliers before importing goods. Verify dropshippers, wholesalers, and vendors to prevent counterfeit products and fraud. Check VAT compliance for reverse charge calculations.",
        "b2b-suppliers": "B2B wholesalers and distributors must screen all trading partners. Verify supplier legitimacy before large orders. Detect carousel fraud and compliance issues in supply chains.",
        "freelancers": "Freelancers and consultants should verify client legitimacy before starting projects. Check if potential clients are registered businesses to prevent contract fraud and non-payment.",
        "import-export": "Import/export businesses must verify trading partners across EU borders. Ensure compliance with Intrastat, VAT rules, and reverse charge mechanisms. Prevent carousel fraud in international supply chains.",
        "saas": "SaaS companies need to verify B2B customers for payment risk and fraud. Screen new accounts for legitimacy before providing service access. Reduce churn from fraudulent customer accounts.",
        "manufacturing": "Manufacturers verify raw material suppliers and component vendors. Ensure supply chain continuity and prevent supplier fraud. Screen for compliance and payment risk.",
        "startups": "Startups conduct due diligence on investors, partners, and early customers. Verify business legitimacy before partnerships. Reduce fraud risk in early-stage growth.",
        "agencies": "Agencies verify client legitimacy before starting projects. Check if clients are registered, legitimate businesses to reduce payment risk and contract disputes."
    }
    
    for slug, biz_info in BUSINESS_TYPES.items():
        filename = biz_dir / f"for-{slug}.html"
        content = BUSINESS_TEMPLATE.format(
            title=biz_info["title"],
            desc=biz_info["desc"],
            slug=f"for-{slug}",
            business_type=biz_info["name"],
            use_case_description=use_case_descriptions.get(slug, "")
        )
        filename.write_text(content, encoding="utf-8")
        print(f"✅ Created: public/vat-check/for-{slug}.html")

if __name__ == "__main__":
    print("\n🚀 Generating GEO pages (15 German cities)...")
    create_geo_pages()
    print(f"\n✅ Created {len(CITIES)} GEO pages")
    
    print("\n🚀 Generating Business Type pages (8 industries)...")
    create_business_pages()
    print(f"\n✅ Created {len(BUSINESS_TYPES)} Business Type pages")
    
    print(f"\n✨ Total: {len(CITIES) + len(BUSINESS_TYPES)} new pages generated!")
    print("📍 Pages created in: public/vat-check/")
