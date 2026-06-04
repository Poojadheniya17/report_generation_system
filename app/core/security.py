"""
Typeform webhook signature verification.

Typeform signs each webhook request with HMAC-SHA256 over the raw request
body, using the secret you set when creating the webhook. It sends the result
base64-encoded in the `Typeform-Signature` header as `sha256=<base64>`.

We MUST verify against the raw bytes of the body — not a re-serialized JSON —
because any reordering or whitespace change breaks the HMAC. This is why the
webhook route reads `await request.body()` rather than the parsed JSON.

Docs: https://www.typeform.com/developers/webhooks/secure-your-webhooks/
"""
import base64
import hashlib
import hmac


def compute_signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    return "sha256=" + base64.b64encode(digest).decode("utf-8")


def verify_signature(payload: bytes, secret: str, header_signature: str | None) -> bool:
    """Constant-time comparison of the expected vs received signature."""
    if not secret or not header_signature:
        return False
    expected = compute_signature(payload, secret)
    return hmac.compare_digest(expected, header_signature)
