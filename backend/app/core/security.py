import base64
import hashlib
import hmac
import json
import os
import time

from app.core.config import settings

PBKDF2_ITERATIONS = 260000
TOKEN_MAX_AGE_SECONDS = settings.TOKEN_EXPIRE_MINUTES * 60


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS, salt.hex(), digest.hex()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, AttributeError):
        return False


# Fixed PBKDF2-SHA256 hash used only to equalize login timing between an
# unknown username and a wrong password, reducing account-enumeration signal.
DUMMY_PASSWORD_HASH = hash_password("timing-equalization-dummy-password")


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(payload: dict) -> str:
    now = int(time.time())
    header = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    body = _b64encode(
        json.dumps({**payload, "iat": now, "exp": now + TOKEN_MAX_AGE_SECONDS}).encode("utf-8")
    )
    signing_input = f"{header}.{body}".encode("utf-8")
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header}.{body}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token")

    header, body, signature = parts
    signing_input = f"{header}.{body}".encode("utf-8")
    expected = hmac.new(
        settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    if not hmac.compare_digest(expected, _b64decode(signature)):
        raise ValueError("Invalid token signature")

    payload = json.loads(_b64decode(body).decode("utf-8"))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("Token expired")
    return payload