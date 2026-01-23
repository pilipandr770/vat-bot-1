#!/usr/bin/env python3
"""Submit sitemap to search engines (Google, Bing).

Usage:
  SITEMAP_URL environment variable may be set, otherwise defaults to https://vat-verifizierung.de/sitemap.xml

This script performs the simple ping endpoints used by search engines:
  - Google: http://www.google.com/ping?sitemap=<sitemap>
  - Bing:   http://www.bing.com/webmaster/ping.aspx?siteMap=<sitemap>

It prints HTTP status codes and response bodies for debugging.
"""
import os
import sys
import urllib.parse
import requests


def ping(url: str):
    try:
        r = requests.get(url, timeout=15)
        return r.status_code, r.text[:2000]
    except Exception as e:
        return None, str(e)


def main():
    sitemap = os.getenv('SITEMAP_URL', 'https://vat-verifizierung.de/sitemap.xml')
    enc = urllib.parse.quote_plus(sitemap)

    endpoints = {
        'google': f'http://www.google.com/ping?sitemap={enc}',
        'bing': f'http://www.bing.com/webmaster/ping.aspx?siteMap={enc}'
    }

    print(f"Submitting sitemap: {sitemap}\n")
    for name, endpoint in endpoints.items():
        code, body = ping(endpoint)
        print(f"{name.upper()}: {endpoint}")
        print(f"  status: {code}")
        if body:
            print(f"  body: {body[:500]}\n")


if __name__ == '__main__':
    main()
