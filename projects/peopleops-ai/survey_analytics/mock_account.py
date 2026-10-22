"""Public fake account credentials for this localhost-only survey simulator."""

from secrets import compare_digest

from fastapi import HTTPException, Request

DEMO_API_TOKEN = "FAKE-QUALTRICS-LOCAL-ONLY-NOT-A-REAL-TOKEN"


def require_mock_token(request: Request):
    """Reject missing or incorrect demo tokens before returning the fixed mock export."""
    supplied = request.headers.get("X-API-TOKEN", "")
    if not compare_digest(supplied.encode(), DEMO_API_TOKEN.encode()):
        raise HTTPException(401, "Missing or invalid local mock X-API-TOKEN")


def account_fixture():
    """Describe the fake local account without implying a real Qualtrics subscription."""
    return {
        "account_id": "acct_local_synthetic_001",
        "name": "Local Qualtrics Test Account",
        "synthetic": True,
        "provider": "local_simulator",
        "real_qualtrics_connected": False,
        "token_type": "public demo fixture, not a secret",
        "surveys": ["SV_SYNTHETIC_PULSE_OCT_2026", "SV_SYNTHETIC_SAMSARA_5000"],
    }
