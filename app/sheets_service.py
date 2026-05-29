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
    "https://www.googleapis.com/auth/drive",
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
    try:
        first_row = ws.row_values(1)
        if not first_row:
            ws.insert_row(SHEET_HEADERS, index=1)
            logger.info("Inserted header row into Google Sheet.")
    except Exception as exc:
        logger.warning(f"Could not check/insert headers: {exc}")


def _email_already_logged(ws: gspread.Worksheet, recipient_email: str) -> bool:
    """Check if this email was already sent successfully."""
    try:
        emails_col = ws.col_values(2)  # Column B = Recipient Email
        sent_emails = [e.lower().strip() for e in emails_col[1:]]  # skip header
        return recipient_email.lower().strip() in sent_emails
    except Exception as exc:
        logger.warning(f"Could not check for duplicate email: {exc}")
        return False


async def log_email(
    recipient_email: str,
    subject: str,
    status: str,
    jd: str,
) -> None:
    """Append a row to the Google Sheet log."""
    import asyncio
    loop = asyncio.get_event_loop()

    def _write() -> None:
        try:
            ws = _get_worksheet()
            _ensure_headers(ws)

            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            jd_truncated = jd[:2000] + "…" if len(jd) > 2000 else jd

            row = [timestamp, recipient_email, subject, status, jd_truncated]
            ws.append_row(row, value_input_option="USER_ENTERED")
            logger.info(f"Logged to Google Sheets: {recipient_email} | status={status}")

        except gspread.exceptions.SpreadsheetNotFound:
            logger.error(
                f"Google Sheet '{get_settings().google_sheet_name}' not found. "
                "Check the sheet name and that it's shared with the service account."
            )
        except gspread.exceptions.APIError as exc:
            logger.error(f"Google Sheets API error: {exc}")
        except Exception as exc:
            logger.error(f"Unexpected Sheets error: {type(exc).__name__}: {exc}")

    await loop.run_in_executor(None, _write)


async def is_duplicate(recipient_email: str) -> bool:
    """Check if this email was already sent."""
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