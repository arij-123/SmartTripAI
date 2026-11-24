from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row

from auth import get_current_user
from database import get_connection
from recommendation_service import recommander_voyage
from photo_service import obtenir_photo_ville
from hotel_service import recommander_hotels

router = APIRouter(
    prefix="/profiles",
    tags=["Recommandations"],
)


@router.post("/{profile_id}/recommendations")
def obtenir_recommandations(
    profile_id: int,
    methode: Literal["weighted", "cosine", "knn"] = "weighted",
    current_user: dict = Depends(get_current_user),
):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    budget_total,
                    jours,
                    mois,
                    climat,
                    interets
                FROM profiles
                WHERE id = %s AND user_id = %s
                """,
                (profile_id, current_user["id"]),
            )

            profil = cursor.fetchone()

    if profil is None:
        raise HTTPException(
            status_code=404,
            detail="Profil introuvable.",
        )
    

    resultat = recommander_voyage(profil, methode)
    for destination in resultat["destinations"]:
        # Photo de la destination
        destination["photo"] = obtenir_photo_ville(
            destination["destination"],
            destination["pays"],
        )

        # Les 5 hôtels les mieux classés dans cette ville
        destination["hotels"] = recommander_hotels(
            pays=destination["pays"],
            ville=destination["destination"],
            top_n=5,
        )

    return {
        "profile_id": profil["id"],
        **resultat,
    }