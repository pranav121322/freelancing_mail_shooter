"""
prompt.py — Gemini prompt templates using personal context + resume.
"""

import os
import logging

logger = logging.getLogger(__name__)

CONTEXT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "context.txt")
RESUME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resume.pdf")

SYSTEM_PROMPT = """You are an expert technical recruiter ghostwriter helping a 
software developer craft personalized, professional job application emails.

Your emails:
- Sound human, warm, and confident — never desperate or spammy
- Are concise (under 200 words for the body)
- Pick 2-3 most relevant skills/achievements from the candidate's background that match the JD
- End with a clear, soft call to action
- Use a compelling subject line (under 10 words)

Always respond with ONLY valid JSON in this exact format:
{
  "subject": "...",
  "body": "..."
}

The body should be plain text with \\n for line breaks. No markdown, no HTML tags.
"""


def _load_context() -> str:
    """Load personal context from context.txt."""
    if not os.path.exists(CONTEXT_PATH):
        logger.warning(f"context.txt not found at {CONTEXT_PATH} — using empty context.")
        return ""
    with open(CONTEXT_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
    logger.info("Personal context loaded from context.txt")
    return content


def build_email_prompt(jd: str, sender_name: str) -> str:
    """
    Build Gemini prompt injecting personal context + JD.

    Args:
        jd: Job description from Telegram message.
        sender_name: Sender name from env vars.

    Returns:
        Full prompt string for Gemini.
    """
    context = _load_context()

    context_section = f"""
Candidate Background & Context:
--------------------------------
{context}
--------------------------------
""" if context else ""

    return f"""Write a professional job application email for {sender_name}.
{context_section}
Job Description:
--------------------------------
{jd}
--------------------------------

Instructions:
- Subject: short, role-specific, under 10 words
- Opening paragraph: show genuine interest in THIS specific role
- Middle paragraph: pick 2-3 skills or achievements from the candidate's background 
  that DIRECTLY match what the JD is asking for — be specific, use real numbers/details
- Closing paragraph: soft CTA — ask for a brief call or next steps
- Sign off with: {sender_name}
- Do NOT include placeholder text, fake links, or contact info
- Do NOT say "I came across your posting" — sound direct and confident
- Sound like a real person writing this themselves, not a template

Respond ONLY with valid JSON. No preamble, no explanation.
"""