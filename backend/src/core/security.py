import bcrypt
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from src.core.config import settings


def hash_password(raw_password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(raw_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            raw_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _sign(data: str) -> str:
    digest = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        data.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64url_encode(digest)


def create_jwt_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url_encode(
        json.dumps(payload, separators=(",", ":")).encode()
    )
    signing_input = f"{encoded_header}.{encoded_payload}"
    return f"{signing_input}.{_sign(signing_input)}"


def create_access_token(subject: str) -> str:
    return create_jwt_token(
        subject, "access", timedelta(minutes=settings.jwt_access_ttl_min)
    )


def create_refresh_token(subject: str) -> str:
    return create_jwt_token(
        subject, "refresh", timedelta(days=settings.jwt_refresh_ttl_days)
    )


def decode_jwt_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Некорректный токен") from exc

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected_signature = _sign(signing_input)
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Некорректная подпись токена")

    try:
        payload = json.loads(_b64url_decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Некорректное содержимое токена") from exc

    if payload.get("type") != expected_type:
        raise ValueError("Некорректный тип токена")

    exp = payload.get("exp")
    if not isinstance(exp, int):
        raise ValueError("Некорректный срок действия токена")
    if exp < int(datetime.now(timezone.utc).timestamp()):
        raise ValueError("Токен истек")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Некорректный владелец токена")

    return payload
