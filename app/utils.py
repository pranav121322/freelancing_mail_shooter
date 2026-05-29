"""
utils.py — Shared utility functions: parsing, validation, logging setup.

Parsing is now fully flexible — no format required from the user.
Email is extracted from anywhere in the message (any domain).
Everything else is treated as the job description.
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
    """Validate an email address — any domain (gmail, company, etc.)."""
    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    return bool(re.match(pattern, email.strip()))


def parse_telegram_message(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Flexibly extract email and job description from ANY message format.

    Supported formats (all work):
        1. Completely unformatted:
               "Please send to hr@company.com, we need a Python dev with 5yr exp..."

        2. Labelled (old format still works):
               Email: hr@company.com
               JD: Looking for Python developer...

        3. Mixed / partial — email anywhere, rest is JD

    Strategy:
        - Find the first valid email address anywhere in the text
        - Everything else (with email removed) becomes the JD

    Returns:
        (email, jd) — either can be None if not found.
    """
    email: Optional[str] = None
    jd: Optional[str] = None

    # Match any email address anywhere in the message
    email_pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    email_match = re.search(email_pattern, text)

    if email_match:
        email = email_match.group(0).strip()

        # Remove the email from the text to get the JD
        remaining = text[:email_match.start()] + text[email_match.end():]

        # Clean up common label prefixes like "Email:", "JD:", "Mail:"
        remaining = re.sub(
            r"(?i)(email|mail|jd|job\s*description|to|contact)\s*[:\-]\s*",
            " ",
            remaining,
        )

        # Collapse extra whitespace
        remaining = re.sub(r"\n{3,}", "\n\n", remaining)
        remaining = re.sub(r"[ \t]+", " ", remaining)
        remaining = remaining.strip()

        if remaining:
            jd = remaining

    return email, jd


def truncate(text: str, max_len: int = 500) -> str:
    """Truncate text for safe logging."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"