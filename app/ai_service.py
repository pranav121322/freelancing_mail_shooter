"""
ai_service.py — Google Gemini integration for generating email subject + body.
"""

import json
import logging
from typing import TypedDict

import google.generativeai as genai

from app.config import get_settings
from app.prompt import SYSTEM_PROMPT, build_email_prompt

logger = logging.getLogger(__name__)


class GeneratedEmail(TypedDict):
    subject: str
    body: str


def _get_model() -> genai.GenerativeModel:
    """Initialise and return the Gemini model. Called lazily to avoid startup errors."""
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=10240,
            response_mime_type="application/json",
        ),
    )


async def generate_email(jd: str) -> GeneratedEmail:
    """
    Call Gemini to generate a professional email subject and body.

    Args:
        jd: The job description extracted from the Telegram message.

    Returns:
        A dict with 'subject' and 'body' keys.

    Raises:
        ValueError: If Gemini returns malformed JSON or missing keys.
        RuntimeError: On API-level failures.
    """
    settings = get_settings()
    model = _get_model()
    prompt = build_email_prompt(jd, settings.email_sender_name)

    logger.info("Calling Gemini API to generate email…")
    try:
        response = model.generate_content(prompt)
        raw = response.text.strip()
        logger.debug(f"Gemini raw response: {raw[:300]}")
    except Exception as exc:
        logger.error(f"Gemini API call failed: {exc}")
        raise RuntimeError(f"Gemini API error: {exc}") from exc

    # Parse JSON response
    try:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data: dict = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error(f"Failed to parse Gemini JSON: {raw[:200]}")
        raise ValueError(f"Gemini returned non-JSON response: {exc}") from exc

    if "subject" not in data or "body" not in data:
        raise ValueError(f"Gemini JSON missing required keys: {list(data.keys())}")

    subject = str(data["subject"]).strip()
    body = str(data["body"]).strip()

    if not subject or not body:
        raise ValueError("Gemini returned empty subject or body")

    logger.info(f"Email generated. Subject: '{subject}'")
    return GeneratedEmail(subject=subject, body=body)
