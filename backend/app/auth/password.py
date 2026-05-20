"""argon2id-based password hash / verify.

Per Step 3 TaskBrief §1.3:
- argon2id (passlib[argon2])
- min length 8, max length 128
- email normalization is the caller's responsibility (router/service layer)
"""
from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 128


class PasswordPolicyError(ValueError):
    """Raised when a password does not satisfy the length policy."""


def hash_password(plain: str) -> str:
    if not MIN_PASSWORD_LEN <= len(plain) <= MAX_PASSWORD_LEN:
        raise PasswordPolicyError(
            f"password length must be {MIN_PASSWORD_LEN}-{MAX_PASSWORD_LEN}"
        )
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)
