"""Olivo Chat backend - main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.billing.router import router as billing_router
from app.config import settings
from app.conversations.router import router as conversations_router

app = FastAPI(
    title="Olivo Chat API",
    version="0.1.0",
    description="Chatbot SaaS for restaurants",
)

_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth_router)
app.include_router(conversations_router)
app.include_router(billing_router)


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
