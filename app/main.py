"""
main.py — FastAPI application entry point.
Registers routes, startup/shutdown hooks, and the Telegram webhook endpoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.telegram_bot import process_update, register_webhook, delete_webhook
from app.utils import setup_logging

# ── Logging setup ──────────────────────────────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ── Lifespan (startup + shutdown) ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Register webhook on startup; clean up on shutdown."""
    logger.info("Starting AI Freelancing Mail Shooter…")
    try:
        await register_webhook()
    except Exception as exc:
        logger.error(f"Webhook registration failed: {exc}")
        # Don't crash the app — Railway restarts will retry

    yield  # App is running

    logger.info("Shutting down…")
    await delete_webhook()


# ── App factory ────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Freelancing Mail Shooter",
    description="Telegram-triggered AI email sender for freelance job applications.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    """Root health check — useful for Railway uptime monitoring."""
    return {"status": "ok", "service": "AI Freelancing Mail Shooter"}


@app.get("/health", tags=["Health"])
async def health():
    """Detailed health endpoint."""
    settings = get_settings()
    return {
        "status": "healthy",
        "webhook_url": settings.webhook_url,
        "sheet": settings.google_sheet_name,
        "sender": settings.email_sender,
    }


@app.post("/webhook", tags=["Telegram"])
async def telegram_webhook(request: Request):
    """
    Receive incoming Telegram updates via webhook POST.
    Telegram expects a 200 OK response quickly — processing is kicked off
    as a background task to avoid timeouts.
    """
    try:
        update_data = await request.json()
        logger.debug(f"Webhook payload received: {str(update_data)[:200]}")
    except Exception as exc:
        logger.error(f"Failed to parse webhook payload: {exc}")
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    # Process in background so we return 200 immediately to Telegram
    import asyncio
    asyncio.create_task(process_update(update_data))

    return Response(status_code=status.HTTP_200_OK)


@app.get("/set-webhook", tags=["Telegram"])
async def set_webhook_manually():
    """Manually trigger webhook (re)registration — useful for debugging."""
    try:
        await register_webhook()
        return {"status": "webhook registered", "url": get_settings().webhook_url}
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(exc)},
        )


@app.get("/delete-webhook", tags=["Telegram"])
async def delete_webhook_manually():
    """Remove the current webhook — switch to polling mode."""
    try:
        await delete_webhook()
        return {"status": "webhook deleted"}
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(exc)},
        )
