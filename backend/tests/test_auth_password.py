"""argon2id password module unit tests (Step 3 §1.3)."""
from __future__ import annotations

import pytest

from app.auth.password import (
    MAX_PASSWORD_LEN,
    MIN_PASSWORD_LEN,
    PasswordPolicyError,
    hash_password,
    verify_password,
)


def test_hash_and_verify_roundtrip() -> None:
    plain = "correct_horse_battery_staple"
    hashed = hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$argon2"), "expected argon2 prefix"
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_hash_is_salted_and_non_deterministic() -> None:
    plain = "same-password-twice"
    h1 = hash_password(plain)
    h2 = hash_password(plain)

    assert h1 != h2, "argon2 must use a random salt per hash"
    assert verify_password(plain, h1) is True
    assert verify_password(plain, h2) is True


def test_password_too_short_is_rejected() -> None:
    short = "x" * (MIN_PASSWORD_LEN - 1)
    with pytest.raises(PasswordPolicyError):
        hash_password(short)


def test_password_too_long_is_rejected() -> None:
    long = "x" * (MAX_PASSWORD_LEN + 1)
    with pytest.raises(PasswordPolicyError):
        hash_password(long)


def test_password_at_boundaries_is_accepted() -> None:
    at_min = "a" * MIN_PASSWORD_LEN
    at_max = "b" * MAX_PASSWORD_LEN

    assert verify_password(at_min, hash_password(at_min)) is True
    assert verify_password(at_max, hash_password(at_max)) is True
