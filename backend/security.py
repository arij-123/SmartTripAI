from pwdlib import PasswordHash

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    return password_hasher.verify(password, stored_hash)

load_dotenv(
    Path(__file__).resolve().parent / ".env",
    interpolate=False,
)

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
TOKEN_DURATION_MINUTES = 30

if len(SECRET_KEY) < 64:
    raise RuntimeError("La clé JWT doit contenir au moins 64 caractères.")


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_DURATION_MINUTES),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"require": ["sub", "iat", "exp"]},
    )

    user_id = int(payload["sub"])

    if user_id <= 0:
        raise ValueError("Identifiant invalide")

    return user_id