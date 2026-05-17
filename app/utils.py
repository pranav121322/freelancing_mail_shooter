"""
utils.py — Shared utility functions: parsing, validation, logging setup.
"""

import re
import logging
import sys
from typing import Optional, Tuple


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the entire application."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def is_valid_email(email: str) -> bool:
    """Validate an email address with a strict RFC-compatible regex."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def parse_telegram_message(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse a Telegram message to extract email and job description.

    Expected format (flexible):
        Email: hr@company.com
        JD: <job description text...>

    Returns:
        (email, jd) tuple. Either value is None if not found.
    """
    email: Optional[str] = None
    jd: Optional[str] = None

    # Match "Email:" or "email:" followed by the address
    email_match = re.search(
        r"(?i)^email\s*:\s*(.+)$", text, re.MULTILINE
    )
    if email_match:
        email = email_match.group(1).strip()

    # Match "JD:" or "jd:" followed by everything to end of string
    jd_match = re.search(
        r"(?i)^jd\s*:\s*(.+?)(?=\n(?:email)\s*:|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if jd_match:
        jd = jd_match.group(1).strip()

    return email, jd


def truncate(text: str, max_len: int = 500) -> str:
    """Truncate text for safe logging."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"
