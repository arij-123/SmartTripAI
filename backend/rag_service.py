import json
import os

import httpx
from fastapi import HTTPException
from sklearn.feature_extraction.text import TfidfVectorizer
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from llm_service import appeler_llama

RUBRIQUES = {
    "activites_jour": "Visite et activité en journée",
    "activites_soir": "Sortie en soirée",
    "repas": "Restaurant, café ou adresse où manger",
}


def chercher_fiches(jour, question):
    fiches = []
    for cle, rubrique in RUBRIQUES.items():
        for lieu in jour.get(cle, []):
            fiches.append({
                "lieu": lieu["nom"], "rubrique": rubrique,
                "categorie": lieu.get("categorie"), "horaires": lieu.get("horaires"),
            })
    if not fiches:
        return []

    textes = [" ".join(str(v) for v in fiche.values() if v) for fiche in fiches]
    vectoriseur = TfidfVectorizer(strip_accents="unicode")
    matrice = vectoriseur.fit_transform(textes)
    scores = (matrice @ vectoriseur.transform([question]).T).toarray().ravel()
    indices = scores.argsort(kind="stable")[::-1]
    # Pour une question générale, présenter toute la journée.
    if not scores.any():
        return fiches
    return [fiches[i] for i in indices if scores[i] > 0]

DOSSIER_PAYS = (
    Path(__file__).resolve().parent.parent / "ML" / "documents" / "pays"
)


def normaliser_texte(texte):
    texte = unicodedata.normalize("NFKD", str(texte))
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", texte.lower()))


@lru_cache(maxsize=1)
def indexer_pays():
    """Retrouver une fiche par code, nom français ou nom anglais."""
    index = {}

    for chemin in DOSSIER_PAYS.glob("*.md"):
        contenu = chemin.read_text(encoding="utf-8-sig")
        titre = re.search(r"^#\s+(.+)$", contenu, re.MULTILINE)
        anglais = re.search(
            r"^Nom anglais\s*:\s*(.+?)\.\s*Code\b",
            contenu,
            re.MULTILINE | re.IGNORECASE,
        )

        noms = [chemin.stem]
        if titre:
            noms.append(titre.group(1))
        if anglais:
            noms.append(anglais.group(1))

        for nom in noms:
            index[normaliser_texte(nom)] = chemin

    return index


def lire_passages_pays(pays):
    chemin = indexer_pays().get(normaliser_texte(pays))
    if chemin is None:
        return []

    contenu = chemin.read_text(encoding="utf-8-sig")
    sections = re.split(r"^##\s+(.+)$", contenu, flags=re.MULTILINE)
    passages = []

    for titre, corps in zip(sections[1::2], sections[2::2]):
        lignes = [
            ligne.strip()
            for ligne in corps.splitlines()
            if ligne.strip() and not ligne.startswith("Source géographique")
        ]

        # Quelques exemples suffisent pour une présentation générale.
        if "patrimoine" in normaliser_texte(titre):
            lignes = lignes[:6]

        if lignes:
            passages.append({
                "lieu": f"{pays} · {titre.strip()}",
                "source": chemin.name,
                "texte": "\n".join(lignes),
            })

    return passages

def repondre(destination, jour, question, pays):
    lieux = chercher_fiches(jour, question)
    passages_pays = lire_passages_pays(pays)
    sources = lieux + passages_pays

    if not sources:
        return {
            "reponse": f"Aucune information disponible pour {destination}, {pays}.",
            "sources": [],
            "mode": "planning",
        }

    contexte = {
        "ville_selectionnee": destination,
        "pays_selectionne": pays,
        "jour": jour["jour"],
        "planning_du_jour": lieux,
        "fiche_pays": passages_pays,
    }

    return {
        "reponse": appeler_llama(question, contexte),
        "sources": sources,
        "mode": "groq",
    }