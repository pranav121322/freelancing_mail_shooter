"""
telegram_bot.py — Telegram bot logic: message handling, webhook setup, reply sending.
"""

import asyncio
import logging
from typing import Optional

from telegram import Bot, Update
from telegram.error import TelegramError

from app.config import get_settings
from app.utils import parse_telegram_message, is_valid_email, truncate

logger = logging.getLogger(__name__)


def get_bot() -> Bot:
    """Return a configured Telegram Bot instance."""
    return Bot(token=get_settings().telegram_bot_token)


async def send_reply(chat_id: int, text: str) -> None:
    """
    Send a reply message back to the user.

    Args:
        chat_id: Telegram chat ID.
        text: Message text to send.
    """
    bot = get_bot()
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except TelegramError as exc:
        logger.error(f"Failed to send Telegram reply to {chat_id}: {exc}")


async def register_webhook() -> None:
    """Register the FastAPI /webhook endpoint with Telegram on startup."""
    settings = get_settings()
    bot = get_bot()
    webhook_url = settings.webhook_url

    try:
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message"],
            drop_pending_updates=True,
        )
        logger.info(f"Telegram webhook registered: {webhook_url}")
    except TelegramError as exc:
        logger.error(f"Failed to register webhook: {exc}")
        raise


async def delete_webhook() -> None:
    """Remove the Telegram webhook (e.g., on shutdown or for polling mode)."""
    bot = get_bot()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Telegram webhook deleted.")
    except TelegramError as exc:
        logger.warning(f"Failed to delete webhook: {exc}")


async def process_update(update_data: dict) -> None:
    """
    Full pipeline: parse update → validate → generate email → send → log → reply.

    Args:
        update_data: Raw JSON dict from Telegram webhook payload.
    """
    # Avoid circular imports at module level
    from app.ai_service import generate_email
    from app.email_service import send_email
    from app.sheets_service import log_email, is_duplicate

    settings = get_settings()

    # Build Update object
    bot = get_bot()
    update = Update.de_json(update_data, bot)

    message = update.effective_message
    if not message or not message.text:
        logger.debug("Received non-text update — ignoring.")
        return

    chat_id: int = message.chat_id
    raw_text: str = message.text

    logger.info(f"Received message from chat_id={chat_id}: {truncate(raw_text, 100)}")

    # ── 1. Parse email + JD ──────────────────────────────────────────────────
    email, jd = parse_telegram_message(raw_text)

    if not email:
        await send_reply(
            chat_id,
            "❌ <b>Missing email.</b>\n\n"
            "Please format your message like this:\n\n"
            "<code>Email: hr@company.com\nJD: We are looking for…</code>",
        )
        return

    if not is_valid_email(email):
        await send_reply(
            chat_id,
            f"❌ <b>Invalid email address:</b> <code>{email}</code>\n"
            "Please double-check and try again.",
        )
        return

    if not jd:
        await send_reply(
            chat_id,
            "❌ <b>Missing job description.</b>\n\n"
            "Please include a JD section:\n\n"
            "<code>Email: hr@company.com\nJD: We are looking for…</code>",
        )
        return

    # ── 2. Duplicate check ───────────────────────────────────────────────────
    if await is_duplicate(email):
        await send_reply(
            chat_id,
            f"⚠️ Email already sent to <code>{email}</code> previously.\n"
            "Skipping to prevent duplicate outreach.",
        )
        await log_email(email, subject="—", status="duplicate", jd=jd)
        return

    await send_reply(chat_id, f"⏳ Generating personalised email for <code>{email}</code>…")

    # ── 3. Generate email via Gemini ─────────────────────────────────────────
    try:
        generated = await generate_email(jd)
        subject = generated["subject"]
        body = generated["body"]
    except Exception as exc:
        logger.error(f"AI generation failed: {exc}")
        await send_reply(
            chat_id,
            "❌ <b>AI generation failed.</b>\n"
            f"Error: {str(exc)[:200]}\n\nPlease try again.",
        )
        await log_email(email, subject="—", status=f"ai_error: {exc}", jd=jd)
        return

    # ── 4. Rate-limiting delay ───────────────────────────────────────────────
    await asyncio.sleep(settings.rate_limit_delay)

    # ── 5. Send email via Brevo ──────────────────────────────────────────────
    try:
        await send_email(
            recipient_email=email,
            subject=subject,
            body=body,
        )
    except Exception as exc:
        logger.error(f"Email send failed: {exc}")
        await send_reply(
            chat_id,
            "❌ <b>Failed to send email.</b>\n"
            f"Error: {str(exc)[:200]}\n\nPlease check your Brevo credentials.",
        )
        await log_email(email, subject=subject, status=f"send_error: {exc}", jd=jd)
        return

    # ── 6. Log to Google Sheets ──────────────────────────────────────────────
    await log_email(email, subject=subject, status="sent", jd=jd)

    # ── 7. Confirmation reply ────────────────────────────────────────────────
    await send_reply(
        chat_id,
        f"✅ <b>Email sent successfully!</b>\n\n"
        f"📧 <b>To:</b> <code>{email}</code>\n"
        f"📝 <b>Subject:</b> {subject}\n"
        f"📊 Logged to Google Sheets.",
    )
