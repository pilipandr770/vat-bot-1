"""
Username OSINT Adapter
======================
Checks whether a username exists on ~30 popular platforms by making
HTTP GET requests to public profile URLs.

No external packages needed — only `requests` (already installed)
and `concurrent.futures` (stdlib).

Detection logic:
  - 200 response  → profile likely exists  (FOUND)
  - 404 response  → profile not found      (NOT_FOUND)
  - redirect to login/home page → NOT_FOUND (platform hides non-existing users)
  - timeout / connection error → UNKNOWN
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict

import requests

logger = logging.getLogger(__name__)

# ── Platform definitions ──────────────────────────────────────────────────────
# Each entry: url_template, category, not_found_redirects_to (optional substring
# in final URL that indicates "user does not exist"), expected_status

PLATFORMS: list[dict] = [
    # ── Business / Professional ───────────────────────────────────────────────
    {
        "name": "LinkedIn",
        "url": "https://www.linkedin.com/in/{username}",
        "category": "Business",
        "not_found_strings": ["authwall", "login", "signup"],
    },
    {
        "name": "XING",
        "url": "https://www.xing.com/profile/{username}",
        "category": "Business",
        "not_found_strings": ["404", "not-found"],
    },
    {
        "name": "GitHub",
        "url": "https://github.com/{username}",
        "category": "Tech",
        "not_found_strings": [],
    },
    {
        "name": "GitLab",
        "url": "https://gitlab.com/{username}",
        "category": "Tech",
        "not_found_strings": [],
    },
    {
        "name": "Bitbucket",
        "url": "https://bitbucket.org/{username}",
        "category": "Tech",
        "not_found_strings": [],
    },
    {
        "name": "StackOverflow",
        "url": "https://stackoverflow.com/users/{username}",
        "category": "Tech",
        "not_found_strings": [],
    },
    {
        "name": "HackerNews",
        "url": "https://news.ycombinator.com/user?id={username}",
        "category": "Tech",
        "not_found_strings": ["No such user"],
    },
    {
        "name": "Dev.to",
        "url": "https://dev.to/{username}",
        "category": "Tech",
        "not_found_strings": [],
    },
    {
        "name": "Medium",
        "url": "https://medium.com/@{username}",
        "category": "Tech",
        "not_found_strings": ["404"],
    },
    {
        "name": "ProductHunt",
        "url": "https://www.producthunt.com/@{username}",
        "category": "Tech",
        "not_found_strings": [],
    },
    # ── Social ────────────────────────────────────────────────────────────────
    {
        "name": "Twitter / X",
        "url": "https://x.com/{username}",
        "category": "Social",
        "not_found_strings": [],
    },
    {
        "name": "Instagram",
        "url": "https://www.instagram.com/{username}/",
        "category": "Social",
        "not_found_strings": ["login"],
    },
    {
        "name": "Facebook",
        "url": "https://www.facebook.com/{username}",
        "category": "Social",
        "not_found_strings": ["login", "checkpoint"],
    },
    {
        "name": "TikTok",
        "url": "https://www.tiktok.com/@{username}",
        "category": "Social",
        "not_found_strings": [],
    },
    {
        "name": "YouTube",
        "url": "https://www.youtube.com/@{username}",
        "category": "Social",
        "not_found_strings": [],
    },
    {
        "name": "Pinterest",
        "url": "https://www.pinterest.com/{username}/",
        "category": "Social",
        "not_found_strings": [],
    },
    {
        "name": "Reddit",
        "url": "https://www.reddit.com/user/{username}",
        "category": "Social",
        "not_found_strings": [],
    },
    {
        "name": "Tumblr",
        "url": "https://{username}.tumblr.com",
        "category": "Social",
        "not_found_strings": [],
    },
    # ── Creative ──────────────────────────────────────────────────────────────
    {
        "name": "Behance",
        "url": "https://www.behance.net/{username}",
        "category": "Creative",
        "not_found_strings": [],
    },
    {
        "name": "Dribbble",
        "url": "https://dribbble.com/{username}",
        "category": "Creative",
        "not_found_strings": [],
    },
    {
        "name": "SoundCloud",
        "url": "https://soundcloud.com/{username}",
        "category": "Creative",
        "not_found_strings": [],
    },
    {
        "name": "Vimeo",
        "url": "https://vimeo.com/{username}",
        "category": "Creative",
        "not_found_strings": [],
    },
    {
        "name": "Flickr",
        "url": "https://www.flickr.com/people/{username}",
        "category": "Creative",
        "not_found_strings": [],
    },
    # ── Other ─────────────────────────────────────────────────────────────────
    {
        "name": "Telegram",
        "url": "https://t.me/{username}",
        "category": "Messaging",
        "not_found_strings": [],
    },
    {
        "name": "Keybase",
        "url": "https://keybase.io/{username}",
        "category": "Messaging",
        "not_found_strings": [],
    },
    {
        "name": "Patreon",
        "url": "https://www.patreon.com/{username}",
        "category": "Other",
        "not_found_strings": [],
    },
    {
        "name": "Twitch",
        "url": "https://www.twitch.tv/{username}",
        "category": "Other",
        "not_found_strings": [],
    },
    {
        "name": "Steam",
        "url": "https://steamcommunity.com/id/{username}",
        "category": "Other",
        "not_found_strings": ["The specified profile could not be found"],
    },
    {
        "name": "Spotify",
        "url": "https://open.spotify.com/user/{username}",
        "category": "Other",
        "not_found_strings": [],
    },
    {
        "name": "Gravatar",
        "url": "https://en.gravatar.com/{username}",
        "category": "Other",
        "not_found_strings": [],
    },
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
_TIMEOUT = 4  # seconds per request (cloud IPs often blocked; 4s avoids 30×8=240s worst case)


class PlatformResult(TypedDict):
    platform: str
    category: str
    url: str
    status: str   # "found" | "not_found" | "unknown"


def _check_one(username: str, platform: dict) -> PlatformResult:
    """Check a single platform. Never raises — returns 'unknown' on any error."""
    url = platform["url"].format(username=username)
    result: PlatformResult = {
        "platform": platform["name"],
        "category": platform["category"],
        "url": url,
        "status": "unknown",
    }
    try:
        resp = requests.get(
            url,
            headers=_HEADERS,
            timeout=_TIMEOUT,
            allow_redirects=True,
        )
        final_url = resp.url.lower()

        # Check if redirect landed on a "not found" indicator
        not_found_strings = platform.get("not_found_strings", [])
        redirected_away = any(s in final_url for s in not_found_strings)

        # Also check response body for text-based not-found signals
        body_not_found = False
        if not_found_strings:
            body_snippet = resp.text[:2000].lower()
            body_not_found = any(s.lower() in body_snippet for s in not_found_strings)

        if redirected_away or body_not_found:
            result["status"] = "not_found"
        elif resp.status_code == 200:
            result["status"] = "found"
        elif resp.status_code == 404:
            result["status"] = "not_found"
        else:
            result["status"] = "unknown"

    except requests.exceptions.Timeout:
        result["status"] = "unknown"
    except Exception as exc:
        logger.debug(f"Username check error for {platform['name']}: {exc}")
        result["status"] = "unknown"

    return result


def check_username(username: str, max_workers: int = 15) -> list[PlatformResult]:
    """
    Check username across all platforms in parallel.

    Returns a list of PlatformResult dicts sorted by category then platform name.
    Takes ~10-15 seconds for 30 platforms with max_workers=15.
    """
    username = username.strip().lstrip("@")
    if not username:
        return []

    results: list[PlatformResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_check_one, username, p): p for p in PLATFORMS
        }
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                p = futures[future]
                logger.warning(f"Future failed for {p['name']}: {exc}")

    # Sort: found first, then by category, then by name
    order = {"found": 0, "not_found": 1, "unknown": 2}
    results.sort(key=lambda r: (order.get(r["status"], 9), r["category"], r["platform"]))
    return results
