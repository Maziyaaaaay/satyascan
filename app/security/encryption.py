import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    key = settings.field_encryption_key
    if not key:
        # Dev-only fallback: an ephemeral key generated once per process.
        # Anything encrypted with it is unreadable after a restart - set
        # FIELD_ENCRYPTION_KEY in .env for any persistent deployment.
        key = Fernet.generate_key().decode("utf-8")
    return Fernet(key.encode("utf-8"))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")


def hash_for_lookup(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
