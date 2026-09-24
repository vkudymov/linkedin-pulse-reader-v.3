from __future__ import annotations

import base64
import mimetypes
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as PyEmailMessage
from typing import Sequence

from .types import EmailAttachment, EmailMessage, EmailTransport, SendResult


@dataclass(frozen=True, slots=True)
class SmtpTransport(EmailTransport):
    """
    Optional portable transport (for non-Supabase projects).
    Use STARTTLS unless you know your SMTP server expects implicit TLS.
    """

    host: str
    port: int
    username: str
    password: str
    from_email: str
    use_starttls: bool = True

    def send(self, *, message: EmailMessage) -> SendResult:
        try:
            msg = PyEmailMessage()
            msg["From"] = self.from_email
            msg["To"] = message.to_email
            msg["Subject"] = message.subject
            msg.set_content(message.body_text or "")

            for a in message.attachments or ():
                ctype = a.mime_type or mimetypes.guess_type(a.filename)[0] or "application/octet-stream"
                maintype, subtype = (ctype.split("/", 1) + ["octet-stream"])[:2]
                msg.add_attachment(a.content, maintype=maintype, subtype=subtype, filename=a.filename)

            with smtplib.SMTP(self.host, self.port, timeout=30) as s:
                if self.use_starttls:
                    s.starttls()
                if self.username:
                    s.login(self.username, self.password)
                s.send_message(msg)

            return SendResult(ok=True, provider="smtp", message_id=None)
        except Exception as e:
            return SendResult(ok=False, provider="smtp", error=str(e))


def to_base64_attachment(a: EmailAttachment) -> dict[str, str]:
    return {
        "filename": a.filename,
        "mime_type": a.mime_type,
        "content_base64": base64.b64encode(a.content).decode("ascii"),
    }


def to_base64_attachments(attachments: Sequence[EmailAttachment]) -> list[dict[str, str]]:
    return [to_base64_attachment(a) for a in attachments]

