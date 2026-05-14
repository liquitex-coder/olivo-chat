"""Olivo Chat backend - main FastAPI application."""
from fastapi import FastAPI

from app.config import settings

app = FastAPI(
    title="Olivo Chat API",
    version="0.1.0",
    description="Chatbot SaaS for restaurants - Step 1 skeleton",
)


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
