"""
email_service.py — Gmail SMTP with resume attachment. No email.mime dependency.
"""

import asyncio
import base64
import logging
import os
import smtplib
import mimetypes
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 2.0
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

RESUME_PATH = os.path.join(os.path.dirname(__file__), "freelancing_pranav_patil_DE.pdf")


def _load_resume() -> Optional[bytes]:
    if not os.path.exists(RESUME_PATH):
        logger.warning(f"Resume not found at {RESUME_PATH} — sending without attachment.")
        return None
    with open(RESUME_PATH, "rb") as f:
        data = f.read()
    logger.info(f"Resume loaded ({len(data) // 1024} KB)")
    return data


def _build_raw_email(
    sender_name: str,
    sender_email: str,
    recipient_email: str,
    subject: str,
    body: str,
    resume_bytes: Optional[bytes],
    resume_filename: str,
) -> str:
    """Build a raw MIME email string manually — no email.mime imports needed."""
    boundary = "===============mailshooter_boundary_9999=="

    html_body = "<br>".join(body.split("\n"))
    html = f"""<html><body style="font-family:Georgia,serif;font-size:15px;
color:#222;max-width:600px;margin:40px auto;padding:0 20px;">
<p>{html_body}</p></body></html>"""

    lines = []

    # Headers
    lines.append(f"From: {sender_name} <{sender_email}>")
    lines.append(f"To: {recipient_email}")
    lines.append(f"Subject: {subject}")
    lines.append("MIME-Version: 1.0")
    lines.append(f'Content-Type: multipart/mixed; boundary="{boundary}"')
    lines.append("")

    # Body part
    inner_boundary = "===============mailshooter_inner_9999=="
    lines.append(f"--{boundary}")
    lines.append(f'Content-Type: multipart/alternative; boundary="{inner_boundary}"')
    lines.append("")

    # Plain text
    lines.append(f"--{inner_boundary}")
    lines.append("Content-Type: text/plain; charset=utf-8")
    lines.append("Content-Transfer-Encoding: 7bit")
    lines.append("")
    lines.append(body)
    lines.append("")

    # HTML
    lines.append(f"--{inner_boundary}")
    lines.append("Content-Type: text/html; charset=utf-8")
    lines.append("Content-Transfer-Encoding: 7bit")
    lines.append("")
    lines.append(html)
    lines.append("")
    lines.append(f"--{inner_boundary}--")
    lines.append("")

    # Resume attachment
    if resume_bytes:
        encoded = base64.b64encode(resume_bytes).decode("ascii")
        lines.append(f"--{boundary}")
        lines.append("Content-Type: application/pdf")
        lines.append("Content-Transfer-Encoding: base64")
        lines.append(f'Content-Disposition: attachment; filename="{resume_filename}"')
        lines.append("")
        # Split base64 into 76-char lines (RFC 2045)
        for i in range(0, len(encoded), 76):
            lines.append(encoded[i:i+76])
        lines.append("")

    lines.append(f"--{boundary}--")

    return "\r\n".join(lines)


def _send_via_gmail(recipient_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    resume_bytes = _load_resume()
    resume_filename = f"{settings.email_sender_name.replace(' ', '_')}_Resume.pdf"

    raw = _build_raw_email(
        sender_name=settings.email_sender_name,
        sender_email=settings.email_sender,
        recipient_email=recipient_email,
        subject=subject,
        body=body,
        resume_bytes=resume_bytes,
        resume_filename=resume_filename,
    )

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.email_sender, settings.gmail_app_password)
        server.sendmail(settings.email_sender, recipient_email, raw)


async def send_email(recipient_email: str, subject: str, body: str) -> bool:
    last_error: Optional[Exception] = None
    loop = asyncio.get_event_loop()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[Attempt {attempt}/{MAX_RETRIES}] Sending to {recipient_email}...")
            await loop.run_in_executor(
                None,
                lambda: _send_via_gmail(recipient_email, subject, body),
            )
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
        except Exception as exc:
            last_error = exc
            logger.warning(f"Gmail SMTP error (attempt {attempt}): {exc}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF * attempt)

    raise RuntimeError(
        f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}"
    )