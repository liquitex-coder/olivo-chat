"""pytest 収集前の環境変数と DB フィクスチャ。"""
from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_ENV: dict[str, str] = {
    "DATABASE_URL": "postgresql://olivo:olivo_dev_password@localhost:5432/olivo_chat",
    "JWT_SECRET": "test_jwt_secret_for_pytest_only",
    "JWT_ACCESS_TTL": "900",
    "JWT_REFRESH_TTL": "2592000",
    "ANTHROPIC_API_KEY": "sk-ant-test-placeholder",
    "CLAUDE_MODEL": "claude-haiku-4-5-20251001",
    "STRIPE_SECRET_KEY": "sk_test_placeholder",
    "STRIPE_WEBHOOK_SECRET": "whsec_placeholder",
    "STRIPE_PRICE_PRO": "price_placeholder_pro",
    "STRIPE_PRICE_BUSINESS": "price_placeholder_business",
    "CORS_ORIGINS": "http://localhost:5173,http://localhost:5174",
    "EMBED_BASE_URL": "http://localhost:5174",
    "ADMIN_BASE_URL": "http://localhost:5173",
    "API_BASE_URL": "http://localhost:8000",
    "VITE_API_BASE_URL": "http://localhost:8000",
}

for _key, _val in _DEFAULT_ENV.items():
    os.environ.setdefault(_key, _val)

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.main import app  # noqa: E402

_ALL_TABLES = "tenants, users, refresh_tokens, conversations, messages"


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """テストセッション開始時に Alembic でスキーマを適用する。

    Step 2.1 で解決済み: `db/init/00-create-app-user.sql` が olivo を
    NOSUPERUSER NOBYPASSRLS で作成するため、RLS テスト（conversations /
    messages / refresh_tokens）は本物の RLS 制約下で PASS する。
    """
    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """各テスト後にロールバックする非同期 DB セッション。"""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    """API-level tests commit real rows; truncate before each test for isolation."""
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {_ALL_TABLES} CASCADE"))
    yield


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """httpx client bound to the FastAPI app via ASGI transport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
