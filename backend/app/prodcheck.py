"""Production-readiness check: refuse to ship dev placeholders as real secrets.

Pure, dependency-free helper so it can run in tests and in a deploy preflight.
INV-2: no obvious placeholder / dev value may reach a production secret slot.
"""
from __future__ import annotations

# Secret-bearing env keys that must hold real, non-placeholder values in prod.
SECRET_ENV_KEYS = (
    "DATABASE_URL",
    "JWT_SECRET",
    "ANTHROPIC_API_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
)

# Substrings (case-insensitive) that mark a value as a dev/demo placeholder.
_PLACEHOLDER_MARKERS = (
    "placeholder",
    "change_me",
    "do_not_use",
    "dev_password",
    "dev_jwt",
    "localhost",
    "sk-ant-test",
    "sk_test_",
    "whsec_placeholder",
    "example.test",
)


def insecure_env_keys(env: dict[str, str]) -> list[str]:
    """Return the secret keys that are missing or still hold a dev placeholder."""
    bad: list[str] = []
    for key in SECRET_ENV_KEYS:
        value = env.get(key, "")
        if not value:
            bad.append(key)
            continue
        lowered = value.lower()
        if any(marker in lowered for marker in _PLACEHOLDER_MARKERS):
            bad.append(key)
    return sorted(bad)


def is_production_ready(env: dict[str, str]) -> bool:
    """True iff every secret slot holds a real (non-placeholder) value."""
    return not insecure_env_keys(env)
