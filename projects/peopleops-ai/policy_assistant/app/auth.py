import hashlib
import hmac
import time
from fastapi import HTTPException


def authenticate_session(header, identity_provider):
    """Authenticate a bearer session without accepting identity or role claims from the request."""
    scheme, _, token = (header or "").partition(" ")
    digest = hashlib.sha256(token.encode()).hexdigest()
    for expected, principal in identity_provider.credential_entries():
        if scheme.lower() == "bearer" and token and hmac.compare_digest(digest, expected) and principal.active:
            return principal
    raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})


def slack_signature(body, timestamp, secret):
    """Sign exact request bytes using Slack's v0 HMAC format."""
    base = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def verify_slack(body, timestamp, signature, settings, now=None):
    """Validate transport signature and timestamp separately from employee authentication."""
    try:
        fresh = abs((time.time() if now is None else now) - int(timestamp)) <= settings.slack_max_age_seconds
    except (ValueError, TypeError):
        fresh = False
    expected = slack_signature(body, timestamp or "", settings.slack_signing_secret.get_secret_value())
    if not fresh or not hmac.compare_digest(expected, signature or ""):
        raise HTTPException(401, "Slack request verification failed")
