import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_hasher = PasswordHasher()
SESSION_HOURS = 8

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, stored: str) -> bool:
    try:
        return _hasher.verify(stored, password)
    except (VerifyMismatchError, VerificationError):
        return False

def new_token():
    return secrets.token_urlsafe(32)

def token_digest(token: str):
    return hashlib.sha256(token.encode()).hexdigest()

def expiration():
    return datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
