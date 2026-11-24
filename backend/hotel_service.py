import json
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd


CSV_PATH = (
    Path(__file__).resolve().parent.parent
    / "ML"
    / "dataset"
    / "hotel_recommendation_data.csv"
)

COLONNES = [
    "hotel_id",
    "hotel_name",
    "country",
    "city",
    "stars",
    "user_rating",
    "positive_ratio",
    "reviews_analyzed",
    "recommendation_score",
]

COLONNES_NUMERIQUES = [
    "stars",
    "user_rating",
    "positive_ratio",
    "reviews_analyzed",
    "recommendation_score",
]


def normaliser(valeur):
    if pd.isna(valeur):
        return ""

    texte = unicodedata.normalize(
        "NFKD", str(valeur).strip().casefold()
    )
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )
    return " ".join(texte.split())


def normaliser_pays(valeur):
    texte = normaliser(valeur)

    correspondances = {
        "united kingdom (uk)": "united kingdom",
        "uk": "united kingdom",
        "usa": "united states",
        "united states of america": "united states",
    }

    return correspondances.get(texte, texte)


def normaliser_ville(valeur):
    texte = normaliser(valeur)

    correspondances = {
        "new york city": "new york",
    }

    return correspondances.get(texte, texte)


@lru_cache(maxsize=1)
def charger_hotels():
    if not CSV_PATH.is_file():
        raise FileNotFoundError(
            f"Fichier des hôtels introuvable : {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH)

    manquantes = set(COLONNES) - set(df.columns)
    if manquantes:
        raise ValueError(
            f"Colonnes manquantes : {sorted(manquantes)}"
        )

    for colonne in COLONNES_NUMERIQUES:
        df[colonne] = pd.to_numeric(
            df[colonne], errors="coerce"
        )

    df["_pays"] = df["country"].map(normaliser_pays)
    df["_ville"] = df["city"].map(normaliser_ville)

    return df


def recommander_hotels(
    pays,
    ville=None,
    etoiles=None,
    top_n=5,
):
    if top_n < 1 or not normaliser_pays(pays):
        return []

    df = charger_hotels()

    masque = df["_pays"] == normaliser_pays(pays)

    if ville is not None:
        ville_normalisee = normaliser_ville(ville)

        if not ville_normalisee:
            return []

        masque = masque & (df["_ville"] == ville_normalisee)

    if etoiles is not None:
        masque = masque & (df["stars"] >= etoiles)

    resultats = (
        df.loc[masque]
        .dropna(subset=["hotel_id", "recommendation_score"])
        .sort_values(
            "recommendation_score",
            ascending=False,
            kind="stable",
        )
        .drop_duplicates(subset=["hotel_id"])
        .head(top_n)
    )

    return json.loads(
        resultats[COLONNES].to_json(
            orient="records",
            force_ascii=False,
        )
    )