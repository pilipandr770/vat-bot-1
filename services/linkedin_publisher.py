"""
LinkedIn Company Page Publisher
================================
Publishes blog posts to the VAT Verifizierung LinkedIn Company Page.

Two auth methods (tried in order):
  1. Email + Password  — env vars LINKEDIN_EMAIL + LINKEDIN_PASSWORD
     Uses unofficial linkedin-api library. Requires user to be org admin.
  2. OAuth2 token      — env var LINKEDIN_ACCESS_TOKEN or DB LinkedInToken table
     Official API, needs w_organization_social scope.

Env vars:
  LINKEDIN_EMAIL            – LinkedIn account email (admin of org page)
  LINKEDIN_PASSWORD         – LinkedIn account password
  LINKEDIN_ORGANIZATION_ID  – numeric org ID (111149982)
  # OAuth2 (optional fallback):
  LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET, LINKEDIN_ACCESS_TOKEN
"""

import os
import logging
import requests
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

LINKEDIN_AUTH_URL    = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL   = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_UGC_URL     = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"

SCOPES = "openid profile w_member_social w_organization_social r_organization_social"


# ─── Config helpers ──────────────────────────────────────────────────────────

def _client_id() -> str:
    return os.environ.get("LINKEDIN_CLIENT_ID", "")

def _client_secret() -> str:
    return os.environ.get("LINKEDIN_CLIENT_SECRET", "")

def _org_id() -> str:
    return os.environ.get("LINKEDIN_ORGANIZATION_ID", "")

def _email() -> str:
    return os.environ.get("LINKEDIN_EMAIL", "")

def _password() -> str:
    return os.environ.get("LINKEDIN_PASSWORD", "")

def _access_token() -> str:
    """Return stored OAuth token: DB first, then env var."""
    try:
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


# ─── Email/Password publishing (unofficial linkedin-api) ─────────────────────

def _publish_with_email(title: str, url: str, summary: str) -> dict:
    """
    Post to LinkedIn company page using email + password.
    Uses unofficial linkedin-api library (tomquirk/linkedin-api).
    The authenticated account must be an admin of the organization page.
    """
    try:
        from linkedin_api import Linkedin
    except ImportError:
        raise RuntimeError("linkedin-api not installed. Run: pip install linkedin-api==2.1.1")

    email = _email()
    password = _password()
    org_id = _org_id()

    if not email or not password:
        raise RuntimeError("LINKEDIN_EMAIL / LINKEDIN_PASSWORD not configured")
    if not org_id:
        raise RuntimeError("LINKEDIN_ORGANIZATION_ID not configured")

    logger.info("LinkedIn: authenticating as %s (email/password)", email)
    api = Linkedin(email, password)

    commentary = f"{title}\n\n{summary[:250]}\n\n🔗 {url}"

    result = api.create_share(
        text=commentary,
        urn=f"urn:li:organization:{org_id}",
    )
    logger.info("LinkedIn (email auth): posted → %s", result)
    return result or {}


# ─── OAuth2 publishing ────────────────────────────────────────────────────────

def _publish_with_oauth(title: str, url: str, summary: str) -> dict:
    """Post using stored OAuth2 access token."""
    token = _access_token()
    org_id = _org_id()

    if not token:
        raise RuntimeError("LinkedIn access token not configured.")
    if not org_id:
        raise RuntimeError("LINKEDIN_ORGANIZATION_ID not set.")

    commentary = f"{title}\n\n{summary[:200]}\n\n🔗 {url}"[:1300]

    payload = {
        "author": f"urn:li:organization:{org_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": commentary},
                "shareMediaCategory": "ARTICLE",
                "media": [{
                    "status": "READY",
                    "description": {"text": summary[:256]},
                    "originalUrl": url,
                    "title": {"text": title[:200]},
                }],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    resp = requests.post(LINKEDIN_UGC_URL, json=payload, headers=headers, timeout=20)
    if resp.status_code in (200, 201):
        logger.info("LinkedIn (OAuth): Artikel veröffentlicht → %s", url)
        return resp.json() if resp.text else {"id": resp.headers.get("x-restli-id", "")}

    try:
        err = resp.json()
    except Exception:
        err = {"raw": resp.text}
    raise RuntimeError(f"LinkedIn OAuth API error {resp.status_code}: {err}")


# ─── Main entry point ─────────────────────────────────────────────────────────

def publish_post(title: str, url: str, summary: str) -> dict:
    """
    Post to LinkedIn company page.
    Priority: email/password → OAuth token.
    Raises RuntimeError if neither method is available.
    """
    if _email() and _password() and _org_id():
        return _publish_with_email(title, url, summary)

    if _access_token() and _org_id():
        return _publish_with_oauth(title, url, summary)

    raise RuntimeError(
        "LinkedIn not configured. Set LINKEDIN_EMAIL + LINKEDIN_PASSWORD + LINKEDIN_ORGANIZATION_ID "
        "or complete OAuth at /admin/linkedin/auth."
    )


def is_configured() -> bool:
    """True if at least one auth method is configured."""
    email_ok = bool(_email() and _password() and _org_id())
    oauth_ok  = bool(_client_id() and _client_secret())
    return email_ok or oauth_ok


def is_authorized() -> bool:
    """True if ready to post right now (no further auth steps needed)."""
    email_ok = bool(_email() and _password() and _org_id())
    oauth_ok  = bool(_access_token() and _org_id())
    return email_ok or oauth_ok

