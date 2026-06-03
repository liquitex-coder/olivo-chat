"""argon2id-based password hashing / verification."""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128


class PasswordPolicyError(ValueError):
    """Raised when a plaintext password violates the length policy."""


def hash_password(plain: str) -> str:
    if not MIN_PASSWORD_LEN <= len(plain) <= MAX_PASSWORD_LEN:
        raise PasswordPolicyError(
            f"password length must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN}"
        )
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)
