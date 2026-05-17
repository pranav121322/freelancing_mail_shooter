"""
email_service.py — Gmail SMTP email sending with retry logic.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 2.0

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def _build_html_body(plain_body: str) -> str:
    lines = plain_body.replace("\r\n", "\n").split("\n")
    paragraphs = "".join(
        f"<p style='margin:0 0 14px 0;line-height:1.6'>{line}</p>"
        if line.strip() else "<br>"
        for line in lines
    )
    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Georgia,serif;font-size:15px;color:#222;
             max-width:600px;margin:40px auto;padding:0 20px;">
  {paragraphs}
</body>
</html>"""


def _send_via_gmail(recipient_email: str, subject: str, body: str) -> None:
    """Blocking Gmail SMTP send — runs in thread pool."""
    settings = get_settings()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.email_sender_name} <{settings.email_sender}>"
    msg["To"] = recipient_email

    msg.attach(MIMEText(body, "plain"))
    msg.attach(MIMEText(_build_html_body(body), "html"))

    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.email_sender, settings.gmail_app_password)
        server.sendmail(settings.email_sender, recipient_email, msg.as_string())


async def send_email(recipient_email: str, subject: str, body: str) -> bool:
    last_error: Optional[Exception] = None
    loop = asyncio.get_event_loop()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"[Attempt {attempt}/{MAX_RETRIES}] Sending email to {recipient_email}…")
            await loop.run_in_executor(
                None, lambda: _send_via_gmail(recipient_email, subject, body)
            )
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
        except Exception as exc:
            last_error = exc
            logger.warning(f"Gmail SMTP error (attempt {attempt}): {exc}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF * attempt)

    raise RuntimeError(
        f"Failed to send email after {MAX_RETRIES} attempts. Last error: {last_error}"
    )