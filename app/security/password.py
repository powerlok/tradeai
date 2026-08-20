import hashlib
import secrets


def hash_password(password: str) -> str:
    # PBKDF2-HMAC-SHA256 with random salt
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return f"{salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        salt, digest = hashed.split('$', 1)
    except Exception:
        return False
    dk = hashlib.pbkdf2_hmac('sha256', plain.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return dk.hex() == digest
