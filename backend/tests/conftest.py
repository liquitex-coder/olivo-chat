"""pytest 収集前に pydantic-settings 用の環境変数を埋める。"""
from __future__ import annotations

import os

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
