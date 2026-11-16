from functools import lru_cache
from pathlib import Path

import pandas as pd


# Racine du projet SmartTripAI.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "ML" / "dataset"

ACTIVITY_COLUMNS = [
    "culture_score",
    "nature_score",
    "adventure_score",
    "gastronomy_score",
    "nightlife_score",
]


@lru_cache(maxsize=1)
def load_destinations() -> pd.DataFrame:
    destination_path = DATA_DIR / "destinations_extended_corrected.csv"
    budget_path = DATA_DIR / "smarttrip_ai_final_clean.csv"

    # 1. Vérifier la présence des fichiers.
    for path in [destination_path, budget_path]:
        if not path.is_file():
            raise FileNotFoundError(f"Fichier introuvable : {path}")

    destinations = pd.read_csv(destination_path)
    budgets = pd.read_csv(budget_path)

    # 2. Vérifier les colonnes nécessaires.
    required_destinations = {
        "country",
        "destination",
        "month",
        "avg_temp_c",
        *ACTIVITY_COLUMNS,
    }
    required_budgets = {
        "country",
        "destination",
        "budget_usd_day",
    }

    for name, data, required in [
        ("Destinations", destinations, required_destinations),
        ("Budgets", budgets, required_budgets),
    ]:
        missing = required - set(data.columns)

        if missing:
            raise ValueError(
                f"{name} : colonnes manquantes : {sorted(missing)}"
            )

        # Retirer les espaces autour des noms sans modifier la casse.
        for column in ["country", "destination"]:
            data[column] = data[column].astype("string").str.strip()

            if data[column].isna().any() or data[column].eq("").any():
                raise ValueError(f"{name} : valeur vide dans {column}")

    # 3. Préparer une seule valeur de budget par destination.
    budgets = budgets[
        ["country", "destination", "budget_usd_day"]
    ].drop_duplicates()

    if budgets.duplicated(["country", "destination"]).any():
        raise ValueError(
            "Plusieurs budgets différents existent pour une destination."
        )

    # Le budget provient explicitement du deuxième CSV.
    destinations = destinations.drop(
        columns=["budget_usd_day"],
        errors="ignore",
    )

    data = destinations.merge(
        budgets,
        on=["country", "destination"],
        how="left",
        validate="many_to_one",
    )

    # 4. Vérifier les données numériques.
    numeric_columns = ACTIVITY_COLUMNS + [
        "month",
        "avg_temp_c",
        "budget_usd_day",
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    invalid = data[numeric_columns].isna().any(axis=1)

    if invalid.any():
        examples = (
            data.loc[invalid, ["country", "destination"]]
            .drop_duplicates()
            .head(5)
            .to_dict("records")
        )
        raise ValueError(
            f"{int(invalid.sum())} lignes incomplètes ou non numériques. "
            f"Exemples : {examples}"
        )

    if not data["month"].isin(range(1, 13)).all():
        raise ValueError("Les mois doivent être des entiers entre 1 et 12.")

    if (data["budget_usd_day"] <= 0).any():
        raise ValueError("Les budgets journaliers doivent être positifs.")

    if data.duplicated(["country", "destination", "month"]).any():
        raise ValueError("Doublons détectés pour une destination et un mois.")

    data["month"] = data["month"].astype(int)

    return data.reset_index(drop=True)