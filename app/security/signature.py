import hashlib
import hmac
from typing import Optional


def verify_signature(payload: bytes, signature_header: Optional[str], app_secret: Optional[str]) -> bool:
    """Verify Meta's X-Hub-Signature-256 header over the raw request body.

    When app_secret is not configured (mock/dev mode, no real WhatsApp app
    yet) the check is skipped and this returns True - callers should log a
    warning in that case so it's visible the check isn't actually running.
    """
    if not app_secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, provided)
