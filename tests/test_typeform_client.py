"""Test TypeformClient against a mocked api.typeform.com using respx."""
import httpx
import respx

from app.services.typeform_client import API_BASE, TypeformClient, TypeformError


@respx.mock
def test_list_forms():
    respx.get(f"{API_BASE}/forms").mock(
        return_value=httpx.Response(200, json={"items": [{"id": "ABC123", "title": "Work Style"}]})
    )
    with TypeformClient("tfp_test") as tf:
        forms = tf.list_forms()
    return forms == [{"id": "ABC123", "title": "Work Style"}]


@respx.mock
def test_list_field_refs():
    respx.get(f"{API_BASE}/forms/ABC123").mock(
        return_value=httpx.Response(200, json={
            "fields": [
                {"ref": "triad_q1", "id": "f1", "title": "I take charge", "type": "opinion_scale"},
                {"ref": "bfi_q1", "id": "f2", "title": "I am outgoing", "type": "opinion_scale"},
            ]
        })
    )
    with TypeformClient("tfp_test") as tf:
        refs = tf.list_field_refs("ABC123")
    return len(refs) == 2 and refs[0]["ref"] == "triad_q1"


@respx.mock
def test_upsert_webhook_sets_secret_and_url():
    route = respx.put(f"{API_BASE}/forms/ABC123/webhooks/assessment-engine").mock(
        return_value=httpx.Response(200, json={
            "id": "wh1", "form_id": "ABC123", "tag": "assessment-engine",
            "url": "https://app.example.com/webhooks/typeform", "enabled": True,
        })
    )
    with TypeformClient("tfp_test") as tf:
        result = tf.upsert_webhook(
            "ABC123", url="https://app.example.com/webhooks/typeform", secret="known_secret"
        )
    sent = route.calls[0].request
    import json as _json
    body = _json.loads(sent.content)
    checks = [
        result["secret"] == "known_secret",
        body["url"] == "https://app.example.com/webhooks/typeform",
        body["enabled"] is True,
        body["secret"] == "known_secret",  # secret must be in the PUT body
        sent.headers["Authorization"] == "Bearer tfp_test",
    ]
    return all(checks)


def test_upsert_rejects_http():
    with TypeformClient("tfp_test") as tf:
        try:
            tf.upsert_webhook("ABC123", url="http://insecure.example.com/hook")
            return False  # should have raised
        except ValueError:
            return True


@respx.mock
def test_auto_generates_secret():
    respx.put(f"{API_BASE}/forms/ABC123/webhooks/assessment-engine").mock(
        return_value=httpx.Response(200, json={"id": "wh1"})
    )
    with TypeformClient("tfp_test") as tf:
        result = tf.upsert_webhook("ABC123", url="https://app.example.com/hook")
    s = result["secret"]
    return isinstance(s, str) and len(s) == 40  # token_hex(20) -> 40 hex chars


@respx.mock
def test_api_error_surfaced():
    respx.get(f"{API_BASE}/forms/BAD").mock(
        return_value=httpx.Response(404, json={"code": "FORM_NOT_FOUND"})
    )
    with TypeformClient("tfp_test") as tf:
        try:
            tf.get_form("BAD")
            return False
        except TypeformError as e:
            return e.status == 404


@respx.mock
def test_delete_webhook():
    route = respx.delete(f"{API_BASE}/forms/ABC123/webhooks/assessment-engine").mock(
        return_value=httpx.Response(204)
    )
    with TypeformClient("tfp_test") as tf:
        tf.delete_webhook("ABC123")
    return route.called


def run():
    tests = [
        ("list_forms", test_list_forms),
        ("list_field_refs (confirm 80 Qs)", test_list_field_refs),
        ("upsert sends url+secret+auth", test_upsert_webhook_sets_secret_and_url),
        ("rejects http url", test_upsert_rejects_http),
        ("auto-generates 40-char secret", test_auto_generates_secret),
        ("surfaces API errors", test_api_error_surfaced),
        ("delete webhook", test_delete_webhook),
    ]
    print("\n  TYPEFORM CLIENT — TEST RESULTS")
    print("  " + "=" * 42)
    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
        except Exception as e:
            ok = False
            print(f"  [ERROR] {name}: {e}")
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        passed += bool(ok)
    print("  " + "=" * 42)
    print(f"  {passed}/{len(tests)} passed\n")
    return passed == len(tests)


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
