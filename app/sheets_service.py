"""
sheets_service.py — Google Sheets logging with duplicate prevention.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from app.config import get_settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SHEET_HEADERS = ["Timestamp", "Recipient Email", "Subject", "Status", "JD"]


def _get_worksheet() -> gspread.Worksheet:
    """Authenticate and return the target Google Sheet worksheet."""
    settings = get_settings()
    creds = Credentials.from_service_account_info(
        settings.google_creds_dict, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open(settings.google_sheet_name)
    return spreadsheet.sheet1


def _ensure_headers(ws: gspread.Worksheet) -> None:
    """Create header row if the sheet is empty."""
    if ws.row_count == 0 or not ws.row_values(1):
        ws.insert_row(SHEET_HEADERS, index=1)
        logger.info("Inserted header row into Google Sheet.")


def _email_already_logged(ws: gspread.Worksheet, recipient_email: str) -> bool:
    """
    Check if the recipient email already exists in the sheet (duplicate prevention).

    Args:
        ws: The active gspread Worksheet object.
        recipient_email: Email address to search for.

    Returns:
        True if a prior successful send exists for this email.
    """
    try:
        # Column B = "Recipient Email" (index 2 in gspread 1-based)
        emails_col = ws.col_values(2)  # header + data rows
        # Skip header row
        sent_emails = [e.lower() for e in emails_col[1:]]
        return recipient_email.lower() in sent_emails
    except Exception as exc:
        logger.warning(f"Could not check for duplicate email: {exc}")
        return False  # Fail open — allow logging


async def log_email(
    recipient_email: str,
    subject: str,
    status: str,
    jd: str,
) -> None:
    """
    Append a row to the Google Sheet log.

    Args:
        recipient_email: Target email address.
        subject: Email subject line.
        status: 'sent' | 'failed' | 'duplicate'
        jd: The original job description text.
    """
    import asyncio

    loop = asyncio.get_event_loop()

    def _write() -> None:
        try:
            ws = _get_worksheet()
            _ensure_headers(ws)

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            # Truncate JD to prevent cell overflow (Google Sheets limit: 50,000 chars)
            jd_truncated = jd[:2000] + "…" if len(jd) > 2000 else jd

            row = [timestamp, recipient_email, subject, status, jd_truncated]
            ws.append_row(row, value_input_option="USER_ENTERED")
            logger.info(
                f"Logged to Google Sheets: {recipient_email} | status={status}"
            )
        except Exception as exc:
            # Sheet logging failure should NOT block the main flow
            logger.error(f"Failed to log to Google Sheets: {exc}")

    await loop.run_in_executor(None, _write)


async def is_duplicate(recipient_email: str) -> bool:
    """
    Async wrapper to check for duplicate sends.

    Args:
        recipient_email: Email to check.

    Returns:
        True if this email was already sent successfully.
    """
    import asyncio

    loop = asyncio.get_event_loop()

    def _check() -> bool:
        try:
            ws = _get_worksheet()
            _ensure_headers(ws)
            return _email_already_logged(ws, recipient_email)
        except Exception as exc:
            logger.warning(f"Duplicate check failed (failing open): {exc}")
            return False

    return await loop.run_in_executor(None, _check)
