import logging

import psycopg
from fastapi import Depends, FastAPI, HTTPException

from database import get_connection
from psycopg.rows import dict_row

from schemas import ProfileCreate
from auth import get_current_user, router as auth_router
from recommendations import router as recommendations_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SmartTrip AI",
    version="0.1.0",
)
app.include_router(auth_router)
app.include_router(recommendations_router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def database_health():
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database();")
                database_name = cursor.fetchone()[0]

        return {
            "status": "ok",
            "database": database_name,
        }

    except psycopg.Error:
        logger.exception("Échec de la connexion à PostgreSQL")

        raise HTTPException(
            status_code=503,
            detail="Connexion à PostgreSQL impossible.",
        ) from None

@app.post("/profiles", status_code=201)
def create_profile(
    profile: ProfileCreate,
    current_user=Depends(get_current_user),
):
    interests = list(dict.fromkeys(profile.interets))

    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO profiles (
                        user_id,
                        budget_total,
                        jours,
                        mois,
                        climat,
                        interets
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *;
                    """,
                    (
                        current_user["id"],
                        profile.budget_total,
                        profile.jours,
                        profile.mois,
                        profile.climat,
                        interests,
                    ),
                )
                saved_profile = cursor.fetchone()

        return saved_profile

    except psycopg.Error:
        logger.error("Impossible d'enregistrer le profil")
        raise HTTPException(
            status_code=503,
            detail="Impossible d'enregistrer le profil.",
        ) from None


@app.get("/profiles")
def list_profiles(current_user=Depends(get_current_user)):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM profiles
                    WHERE user_id = %s
                    ORDER BY created_at DESC, id DESC;
                    """,
                    (current_user["id"],),
                )
                profiles = cursor.fetchall()

        return profiles

    except psycopg.Error:
        logger.error("Impossible de récupérer les profils")
        raise HTTPException(
            status_code=503,
            detail="Impossible de récupérer les profils.",
        ) from None


@app.get("/profiles/{profile_id}")
def get_profile(
    profile_id: int,
    current_user=Depends(get_current_user),
):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM profiles
                    WHERE id = %s AND user_id = %s;
                    """,
                    (profile_id, current_user["id"]),
                )
                profile = cursor.fetchone()

    except psycopg.Error:
        logger.error("Impossible de récupérer le profil")
        raise HTTPException(
            status_code=503,
            detail="Impossible de récupérer le profil.",
        ) from None

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profil introuvable.",
        )

    return profile