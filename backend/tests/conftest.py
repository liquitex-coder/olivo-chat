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

from app.db.session import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    """テストセッション開始時に Alembic でスキーマを適用する。

    Note (Step 2.1 で対処予定):
    Docker postgres image は POSTGRES_USER を SUPERUSER + BYPASSRLS として
    作成するため、現状 RLS テスト 3 件は PASS しない。Step 2.1 で
    docker-compose.yml に init script を追加して olivo を NOSUPERUSER
    NOBYPASSRLS で作成する、または別の app ユーザーを作成して
    そちらでテストを走らせる方針で対処する。
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