from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

bundle = joblib.load(
    BASE_DIR / "ML" / "models" / "smarttrip.joblib"
)
destinations = bundle["df"].copy()

activity_bundle = joblib.load(
    BASE_DIR / "ML" / "models" / "activity_model.joblib"
)

activites = activity_bundle["df"].copy()

categories_smarttrip = activity_bundle["categories"]

INTERETS = [
    "culture",
    "nature",
    "adventure",
    "gastronomy",
    "nightlife",
]

COLONNES_SCORES = [f"{interet}_score" for interet in INTERETS]

TEMPERATURES = {
    "chaud": 29,
    "doux": 21,
    "froid": 9,
}

#def get_activity_name(activity):
 #   for col in ["name_en", "name_fr", "name"]:
  #      value = activity.get(col)

   #     if pd.notna(value):
   #         value = str(value).strip()

   #         if value and value.lower() not in ["none", "nan", "null"]:
   #             return value

   # return "Unnamed activity"

def normaliser(valeur):
    return " ".join(str(valeur).strip().lower().split())


if "name_display" not in activites.columns:
    raise ValueError(
        "La colonne 'name_display' manque dans activity_model.joblib. "
        "Vérifie que ML/models/activity_model.joblib contient bien "
        "le tableau enrichi exporté depuis Kaggle."
    )


# Clés utilisées pour retrouver la ville et éviter les activités répétées.
for colonne in ("country", "destination"):
    activites[f"{colonne}_norm"] = activites[colonne].fillna("").map(normaliser)

activites["name_norm"] = activites["name_display"].fillna("").map(normaliser)

def recommander_destinations(profil, methode="weighted", limite=5):
    budget_jour = float(profil["budget_total"]) / profil["jours"]

    data = destinations.loc[
        (destinations["month"] == profil["mois"])
        & (destinations["budget_usd_day"] <= budget_jour)
    ].copy()

    climat = profil["climat"]

    if climat == "chaud":
        data = data.loc[data["avg_temp_c"] >= 24].copy()
    elif climat == "doux":
        data = data.loc[
            data["avg_temp_c"].between(15, 27)
        ].copy()
    else:
        data = data.loc[data["avg_temp_c"] <= 16].copy()

    if data.empty:
        return data

    # Même normalisation que dans le notebook :
    # min et max calculés sur toutes les destinations.
    minimums = destinations[COLONNES_SCORES].min()
    amplitudes = (
        destinations[COLONNES_SCORES].max() - minimums
    ).replace(0, 1)

    scores_normalises = (
        (data[COLONNES_SCORES] - minimums) / amplitudes
    ).clip(0, 1)

    colonnes = [
        f"{interet}_score"
        for interet in profil["interets"]
        if interet in INTERETS
    ]

    if not colonnes:
        raise ValueError("Aucun intérêt reconnu.")

    valeurs = scores_normalises[colonnes].to_numpy(dtype=float)

    score_activites = (
        0.7 * valeurs.mean(axis=1)
        + 0.3 * valeurs.min(axis=1)
    )

    score_climat = (
        1
        - abs(data["avg_temp_c"] - TEMPERATURES[climat]) / 20
    ).clip(0, 1).to_numpy()

    score_budget = (
        1 - data["budget_usd_day"] / budget_jour
    ).clip(0, 1).to_numpy()

    if methode == "weighted":
        scores = (
            0.7 * score_activites
            + 0.2 * score_climat
            + 0.1 * score_budget
        )

    elif methode == "cosine":
        normes = np.linalg.norm(valeurs, axis=1)
        denominateur = normes * np.sqrt(valeurs.shape[1])

        similarites = np.divide(
            valeurs.sum(axis=1),
            denominateur,
            out=np.zeros(len(valeurs), dtype=float),
            where=denominateur != 0,
        )

        scores = similarites * score_activites

    elif methode == "knn":
        # Score Manhattan utilisé par ton notebook.
        distances = np.abs(valeurs - 1).sum(axis=1)
        scores = 1 / (1 + distances)

    else:
        raise ValueError("Méthode inconnue.")

    data["score"] = scores

    return (
        data.sort_values("score", ascending=False, kind="stable")
        .drop_duplicates(["country", "destination"])
        .head(limite)
        .reset_index(drop=True)
    )


def selection_equilibree(data, preferences, limite):
    """Alterner les centres d'intérêt sans répéter une activité."""
    preferences = list(dict.fromkeys(preferences))

    data = (
        data.sort_values(
            "completude",
            ascending=False,
            kind="stable",
        )
        .drop_duplicates(["country_norm", "destination_norm", "name_norm"])
        .reset_index(drop=True)
    )

    groupes = {
        preference: data.index[
            data["preference_smarttrip"] == preference
        ].tolist()
        for preference in preferences
    }

    selection = []

    while len(selection) < limite:
        ajout = False

        for preference in preferences:
            if groupes[preference]:
                selection.append(groupes[preference].pop(0))
                ajout = True

                if len(selection) == limite:
                    break

        if not ajout:
            break

    # Même vide, le résultat conserve ses colonnes.
    return data.loc[selection].reset_index(drop=True)


def valeur_json(valeur):
    if pd.isna(valeur):
        return None
    if isinstance(valeur, np.generic):
        return valeur.item()
    return valeur


def construire_planning(destination, pays, profil):
    jours = int(profil["jours"])
    preferences = list(dict.fromkeys(profil["interets"]))

    if "rubrique" not in activites.columns:
        raise ValueError(
            "Le fichier activity_model.joblib chargé est une ancienne version. "
            "Utilise celui exporté par le notebook avec la colonne 'rubrique'."
        )

    locales = activites.loc[
        (activites["destination_norm"] == normaliser(destination))
        & (activites["country_norm"] == normaliser(pays))
        & (activites["name_norm"] != "")
    ]

    def choisir_activites(moment, noms_utilises):
        candidates = locales.loc[
            locales["rubrique"].eq("activites")
            & locales["moment"].eq(moment)
            & ~locales["name_norm"].isin(noms_utilises)
        ]

        # Priorité aux intérêts du voyageur.
        choix = selection_equilibree(candidates, preferences, limite=jours)

        # Compléter avec d'autres intérêts si le séjour est plus long.
        manque = jours - len(choix)
        if manque > 0:
            restantes = candidates.loc[
                ~candidates["name_norm"].isin(choix["name_norm"])
            ]
            complement = selection_equilibree(restantes, INTERETS, limite=manque)
            choix = pd.concat([choix, complement], ignore_index=True)

        return choix

    jour = choisir_activites("jour", set())
    noms_utilises = set(jour["name_norm"])

    soir = choisir_activites("soir_possible", noms_utilises)
    noms_utilises.update(soir["name_norm"])

    # Une adresse où manger, même si le voyageur n'a pas coché gastronomie.
    adresses_food = locales.loc[
        locales["rubrique"].eq("repas")
        & ~locales["name_norm"].isin(noms_utilises)
    ]
    repas = selection_equilibree(adresses_food, ["gastronomy"], limite=jours)

    def lieu_pour_ce_jour(table, index):
        if index >= len(table):
            return []

        ligne = table.iloc[index]
        return [{
            "nom": valeur_json(ligne["name_display"]),
            "categorie": valeur_json(ligne["category"]),
            "interet": valeur_json(ligne["preference_smarttrip"]),
            "latitude": valeur_json(ligne["latitude"]),
            "longitude": valeur_json(ligne["longitude"]),
            "horaires": valeur_json(ligne.get("opening_hours")),
            "site_web": valeur_json(ligne.get("website")),
        }]

    planning = [
        {
            "jour": index + 1,
            "activites_jour": lieu_pour_ce_jour(jour, index),
            "activites_soir": lieu_pour_ce_jour(soir, index),
            "repas": lieu_pour_ce_jour(repas, index),
        }
        for index in range(jours)
    ]

    avertissements = []
    for titre, table in [
        ("Activités en journée", jour),
        ("Sorties du soir", soir),
        ("Adresses où manger", repas),
    ]:
        if len(table) < jours:
            avertissements.append(
                f"{titre} : {len(table)} suggestion(s) pour {jours} jour(s)."
            )

    return planning, avertissements


def recommander_voyage(profil, methode="weighted"):
    classement = recommander_destinations(profil, methode)
    resultats = []

    for _, destination in classement.iterrows():
        planning, avertissements = construire_planning(
            destination["destination"],
            destination["country"],
            profil,
        )

        resultats.append({
            "destination": destination["destination"],
            "pays": destination["country"],
            "score": round(float(destination["score"]), 4),
            "budget_estime_par_jour_usd": float(
                destination["budget_usd_day"]
            ),
            "planning": planning,
            "avertissements": avertissements,
        })

    return {
        "methode": methode,
        "nombre_destinations": len(resultats),
        "destinations": resultats,
        "message": (
            None
            if resultats
            else "Aucune destination ne correspond à ces préférences."
        ),
    }