"""Olivo Chat backend - main FastAPI application."""
from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.config import settings
from app.conversations.router import router as conversations_router

app = FastAPI(
    title="Olivo Chat API",
    version="0.1.0",
    description="Chatbot SaaS for restaurants - Step 1 skeleton",
)

app.include_router(auth_router)
app.include_router(conversations_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    """Backend version and configured model."""
    return {
        "version": app.version,
        "claude_model": settings.CLAUDE_MODEL,
    }
