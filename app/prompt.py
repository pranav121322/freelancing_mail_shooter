"""
prompt.py — Gemini prompt templates for generating recruiter outreach emails.
"""

SYSTEM_PROMPT = """You are an expert technical recruiter ghostwriter helping a 
software developer craft personalized, professional job application emails.

Your emails:
- Sound human, warm, and confident — never desperate or spammy
- Are concise (under 200 words for the body)
- Highlight relevant skills from the job description naturally
- End with a clear, soft call to action
- Use a compelling subject line (under 10 words)

Always respond with ONLY valid JSON in this exact format:
{
  "subject": "...",
  "body": "..."
}

The body should be plain text with \\n for line breaks. No markdown, no HTML tags.
"""


def build_email_prompt(jd: str, sender_name: str) -> str:
    """
    Build the user-turn prompt for Gemini given a job description and sender name.

    Args:
        jd: The job description text extracted from the Telegram message.
        sender_name: The sender's name from environment variables.

    Returns:
        A formatted prompt string.
    """
    return f"""Write a professional job application email for {sender_name}.

Job Description:
{jd}

Requirements:
- Subject line: short, specific to the role, under 10 words
- Body: 3-4 short paragraphs
  * Opening: express specific interest in THIS role
  * Middle: connect 2-3 of their stated requirements to concrete experience
  * Closing: soft CTA asking for a brief call or next steps
- Sign off with: {sender_name}
- Do NOT include placeholder text like [Your Name] or [Company]
- Do NOT include fake links, portfolios, or contact info
- Sound like a real person, not a template

Respond ONLY with valid JSON. No preamble, no explanation.
"""
