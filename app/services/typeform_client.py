"""
Typeform management API client.

Lets us configure the webhook programmatically from a Personal Access Token,
so the client (Tripp) only has to hand over a token rather than click through
the Typeform UI. Endpoints used (api.typeform.com):

  GET    /forms                          -> list forms (find the form_id)
  GET    /forms/{form_id}                -> form definition (field refs/titles)
  PUT    /forms/{form_id}/webhooks/{tag} -> create/update webhook (url+enabled+secret)
  GET    /forms/{form_id}/webhooks/{tag} -> inspect webhook
  DELETE /forms/{form_id}/webhooks/{tag} -> remove webhook

Reference:
  https://www.typeform.com/developers/webhooks/walkthroughs/
  https://www.typeform.com/developers/webhooks/secure-your-webhooks/
"""
from __future__ import annotations

import secrets as _secrets
from typing import Any

import httpx

API_BASE = "https://api.typeform.com"
# EU accounts use api.eu.typeform.com — set base_url accordingly if needed.


class TypeformError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"Typeform API {status}: {message}")


class TypeformClient:
    def __init__(self, access_token: str, base_url: str = API_BASE, timeout: float = 15.0):
        if not access_token:
            raise ValueError("A Typeform access token is required.")
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    # -- context manager so callers can `with TypeformClient(...) as tf:` -----
    def __enter__(self) -> "TypeformClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def _request(self, method: str, path: str, **kwargs) -> Any:
        resp = self._client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            # Typeform returns helpful JSON error bodies; surface them.
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise TypeformError(resp.status_code, str(detail))
        if resp.status_code == 204 or not resp.content:
            return None
        return resp.json()

    # -- forms ----------------------------------------------------------------
    def list_forms(self, page_size: int = 200) -> list[dict[str, Any]]:
        data = self._request("GET", "/forms", params={"page_size": page_size})
        return data.get("items", []) if isinstance(data, dict) else []

    def get_form(self, form_id: str) -> dict[str, Any]:
        return self._request("GET", f"/forms/{form_id}")

    def list_field_refs(self, form_id: str) -> list[dict[str, str]]:
        """
        Returns [{ref, id, title, type}] for every field — used to map the
        survey's question refs to the scoring engine. This is how we confirm
        the 80 questions and their refs without guessing.
        """
        form = self.get_form(form_id)
        fields = form.get("fields", [])
        out: list[dict[str, str]] = []
        for f in fields:
            out.append(
                {
                    "ref": f.get("ref", ""),
                    "id": f.get("id", ""),
                    "title": f.get("title", ""),
                    "type": f.get("type", ""),
                }
            )
        return out

    # -- webhooks -------------------------------------------------------------
    def upsert_webhook(
        self,
        form_id: str,
        url: str,
        tag: str = "assessment-engine",
        secret: str | None = None,
        enabled: bool = True,
    ) -> dict[str, Any]:
        """
        Create or update the webhook in ONE call, including the signing secret.
        Returns the webhook object plus the secret we set (Typeform never
        returns the secret back, so we surface what we sent so it can be saved
        into the server's env).
        """
        if not url.lower().startswith("https://"):
            raise ValueError("Typeform requires an https webhook URL with a valid certificate.")
        if secret is None:
            secret = _secrets.token_hex(20)  # matches Typeform's suggested length

        payload = {"url": url, "enabled": enabled, "secret": secret}
        result = self._request("PUT", f"/forms/{form_id}/webhooks/{tag}", json=payload)
        return {"webhook": result, "secret": secret, "tag": tag}

    def get_webhook(self, form_id: str, tag: str = "assessment-engine") -> dict[str, Any]:
        return self._request("GET", f"/forms/{form_id}/webhooks/{tag}")

    def delete_webhook(self, form_id: str, tag: str = "assessment-engine") -> None:
        self._request("DELETE", f"/forms/{form_id}/webhooks/{tag}")
