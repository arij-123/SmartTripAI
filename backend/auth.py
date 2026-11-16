import logging

import psycopg
from psycopg.rows import dict_row

from database import get_connection
from schemas import UserPublic, UserSignup, UserLogin, TokenResponse
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentification"])

from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

@router.post(
    "/signup",
    response_model=UserPublic,
    status_code=201,
)
def signup(data: UserSignup):
    email = str(data.email).lower()
    password_hash = hash_password(data.password.get_secret_value())

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO users (
                        first_name,
                        last_name,
                        email,
                        password_hash
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING
                        id, first_name, last_name, email, created_at;
                    """,
                    (
                        data.first_name,
                        data.last_name,
                        email,
                        password_hash,
                    ),
                )
                user = cursor.fetchone()

        return user

    except psycopg.errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Cette adresse email est déjà utilisée.",
        ) from None

    except psycopg.Error:
        logger.error("Échec de l'enregistrement du compte")
        raise HTTPException(
            status_code=503,
            detail="Impossible de créer le compte pour le moment.",
        ) from None


# Utilisé pour vérifier un mot de passe même si l'email est inconnu.
DUMMY_HASH = hash_password("Compte-fictif-pour-verification")


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin):
    email = str(data.email).lower()

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, password_hash
                    FROM users
                    WHERE LOWER(email) = %s;
                    """,
                    (email,),
                )
                user = cursor.fetchone()

    except psycopg.Error:
        logger.error("Échec de l'accès à la base lors du login")
        raise HTTPException(
            status_code=503,
            detail="Connexion indisponible pour le moment.",
        ) from None

    stored_hash = user["password_hash"] if user else DUMMY_HASH

    password_valid = verify_password(
        data.password.get_secret_value(),
        stored_hash,
    )

    if user is None or not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user["id"]),
        "token_type": "bearer",
        "expires_in": 1800,
    }


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
):
    unauthorized = HTTPException(
        status_code=401,
        detail="Connexion requise ou session expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        user_id = decode_access_token(credentials.credentials)
    except (InvalidTokenError, ValueError, TypeError):
        raise unauthorized from None

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT id, first_name, last_name, email, created_at
                    FROM users
                    WHERE id = %s;
                    """,
                    (user_id,),
                )
                user = cursor.fetchone()

    except psycopg.Error:
        logger.error("Échec de la récupération du compte connecté")
        raise HTTPException(
            status_code=503,
            detail="Service temporairement indisponible.",
        ) from None

    if user is None:
        raise unauthorized

    return user


@router.get("/me", response_model=UserPublic)
def me(current_user=Depends(get_current_user)):
    return current_user