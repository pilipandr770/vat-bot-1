"""
LinkedIn Company Page Publisher
================================
Publishes blog posts to the VAT Verifizierung LinkedIn Company Page.

OAuth2 flow:
  1. Admin visits /admin/linkedin/auth  → redirected to LinkedIn
  2. LinkedIn redirects back to /admin/linkedin/callback with ?code=...
  3. We exchange code for access_token and store it in DB (LinkedInToken table)
     or fall back to LINKEDIN_ACCESS_TOKEN env var.
  4. publish_post() uses the stored token to call UGC Posts API.

Env vars required:
  LINKEDIN_CLIENT_ID        – from LinkedIn Developer App
  LINKEDIN_CLIENT_SECRET    – from LinkedIn Developer App
  LINKEDIN_ORGANIZATION_ID  – numeric org ID (e.g. 111149982), set after first OAuth
  LINKEDIN_ACCESS_TOKEN     – filled automatically after OAuth, or set manually
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# ─── Constants ─────────────────────────────────────────────────────────────────

LINKEDIN_AUTH_URL   = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL  = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_UGC_URL    = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_ORG_POSTS_URL = "https://api.linkedin.com/v2/shares"   # v2 shares API fallback

SCOPES = "openid profile w_member_social w_organization_social r_organization_social"


# ─── Config helpers ─────────────────────────────────────────────────────────────

def _client_id() -> str:
    return os.environ.get("LINKEDIN_CLIENT_ID", "")

def _client_secret() -> str:
    return os.environ.get("LINKEDIN_CLIENT_SECRET", "")

def _org_id() -> str:
    return os.environ.get("LINKEDIN_ORGANIZATION_ID", "")

def _access_token() -> str:
    """Return stored token: DB first, then env var."""
    try:
        from crm.models import db
        from crm.models import LinkedInToken
        token_row = LinkedInToken.query.order_by(LinkedInToken.id.desc()).first()
        if token_row and token_row.access_token:
            return token_row.access_token
    except Exception:
        pass
    return os.environ.get("LINKEDIN_ACCESS_TOKEN", "")


# ─── OAuth2 helpers ─────────────────────────────────────────────────────────────

def get_auth_url(redirect_uri: str, state: str = "vatbot") -> str:
    """Build the LinkedIn OAuth2 authorization URL."""
    params = {
        "response_type": "code",
        "client_id": _client_id(),
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": SCOPES,
    }
    return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> dict:
    """
    Exchange authorization code for access_token.
    Returns dict with keys: access_token, expires_in, refresh_token (if any).
    """
    resp = requests.post(
        LINKEDIN_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_member_id(access_token: str) -> str:
    """Return the 'sub' (member URN ID) from the OpenID userinfo endpoint."""
    resp = requests.get(
        LINKEDIN_PROFILE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("sub", "")


# ─── Publishing ─────────────────────────────────────────────────────────────────

def publish_post(title: str, url: str, summary: str) -> dict:
    """
    Post a link share to the LinkedIn organization page.

    Returns LinkedIn API response dict on success.
    Raises RuntimeError with a human-readable message on failure.
    """
    token = _access_token()
    org_id = _org_id()

    if not token:
        raise RuntimeError("LinkedIn access token not configured. Visit /admin/linkedin/auth to authorize.")
    if not org_id:
        raise RuntimeError("LINKEDIN_ORGANIZATION_ID not set. Complete OAuth first.")

    author = f"urn:li:organization:{org_id}"

    # Truncate summary to LinkedIn limit (256 chars)
    commentary = f"{title}\n\n{summary[:200]}...\n\n🔗 {url}"[:1300]

    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": commentary
                },
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "description": {
                            "text": summary[:256]
                        },
                        "originalUrl": url,
                        "title": {
                            "text": title[:200]
                        }
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    resp = requests.post(LINKEDIN_UGC_URL, json=payload, headers=headers, timeout=20)

    if resp.status_code in (200, 201):
        logger.info("LinkedIn: Artikel veröffentlicht → %s", url)
        return resp.json() if resp.text else {"id": resp.headers.get("x-restli-id", "")}

    # Surface LinkedIn error to caller
    try:
        err = resp.json()
    except Exception:
        err = {"raw": resp.text}
    raise RuntimeError(f"LinkedIn API error {resp.status_code}: {err}")


def is_configured() -> bool:
    """True if minimum env vars are present to attempt publishing."""
    return bool(_client_id() and _client_secret())


def is_authorized() -> bool:
    """True if we have an access token (OAuth completed)."""
    return bool(_access_token() and _org_id())
