from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.request
from dataclasses import dataclass

import certifi

from search_report_mailer.types import EmailMessage, EmailTransport, SendResult


@dataclass(frozen=True, slots=True)
class SupabaseFunctionsEmailTransport(EmailTransport):
    """
    Project-specific transport: calls a Supabase Edge Function to send email.

    Env:
      SUPABASE_URL (e.g. https://xxx.supabase.co)
      SEARCH_REPORT_FUNCTION_SECRET
      SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) for the gateway Authorization header
    """

    supabase_url: str
    function_secret: str
    api_key: str
    function_name: str = "send-search-report"

    def send(self, *, message: EmailMessage) -> SendResult:
        try:
            attachments = list(message.attachments or ())
            if not attachments:
                return SendResult(ok=False, provider="supabase_edge", error="missing attachment")
            if len(attachments) > 1:
                return SendResult(ok=False, provider="supabase_edge", error="only 1 attachment supported")

            a = attachments[0]
            url = self.supabase_url.rstrip("/") + f"/functions/v1/{self.function_name}"
            body = {
                "to": message.to_email,
                "subject": message.subject,
                "body": message.body_text,
                "filename": a.filename,
                "mime_type": a.mime_type,
                "content_base64": base64.b64encode(a.content).decode("ascii"),
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "content-type": "application/json",
                    "authorization": f"Bearer {self.api_key}",
                    "x-search-report-secret": self.function_secret,
                },
                method="POST",
            )
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:  # noqa: S310
                raw = resp.read().decode("utf-8", "replace")
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {"raw": raw}
                if int(getattr(resp, "status", 200)) >= 400:
                    return SendResult(ok=False, provider="supabase_edge", error=str(data), raw=data)
                return SendResult(ok=True, provider="supabase_edge", raw=data)
        except Exception as e:
            return SendResult(ok=False, provider="supabase_edge", error=str(e))


def build_transport_from_env() -> SupabaseFunctionsEmailTransport:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    secret = (os.getenv("SEARCH_REPORT_FUNCTION_SECRET") or "").strip()
    api_key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or "").strip()
    if not url:
        raise RuntimeError("Missing SUPABASE_URL for SupabaseFunctionsEmailTransport")
    if not secret:
        raise RuntimeError("Missing SEARCH_REPORT_FUNCTION_SECRET for SupabaseFunctionsEmailTransport")
    if not api_key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY for SupabaseFunctionsEmailTransport")
    return SupabaseFunctionsEmailTransport(supabase_url=url, function_secret=secret, api_key=api_key)

