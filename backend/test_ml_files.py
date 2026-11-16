from pathlib import Path

import joblib
import pandas as pd

# Dossier principal SmartTripAI
BASE_DIR = Path(__file__).resolve().parent.parent

chemin_destinations = BASE_DIR / "ML" / "models" / "smarttrip.joblib"
chemin_activites = BASE_DIR / "ML" / "dataset" / "all_activites_clean.csv"

# Vérifier la présence des fichiers
for chemin in [chemin_destinations, chemin_activites]:
    if not chemin.is_file():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

# Charger ton export du notebook destinations
bundle = joblib.load(chemin_destinations)
destinations = bundle["df"]

# Charger les activités nettoyées
activites = pd.read_csv(chemin_activites)

# Vérifier les colonnes nécessaires aux recommandations
colonnes_requises = {
    "country_norm",
    "destination_norm",
    "name",
    "name_norm",
    "category",
    "preference_smarttrip",
    "completude",
    "moment",
    "latitude",
    "longitude",
    "opening_hours",
}

manquantes = colonnes_requises - set(activites.columns)

if manquantes:
    raise ValueError(f"Colonnes manquantes : {sorted(manquantes)}")

if destinations.empty or activites.empty:
    raise ValueError("Un des deux tableaux est vide.")

print("Chargement réussi !")
print("Nombre de lignes destinations :", len(destinations))
print("Nombre d’activités :", len(activites))

print("\nExemple de destinations :")
print(destinations[["country", "destination"]].head())

print("\nExemple d’activités :")
print(
    activites[
        ["destination", "name", "preference_smarttrip", "moment"]
    ].head()
)