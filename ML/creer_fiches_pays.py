import json
from pathlib import Path
from urllib.request import urlopen


DOSSIER_ML = Path(__file__).resolve().parent
DOSSIER_FICHES = DOSSIER_ML / "documents" / "pays"

URL_PAYS = "https://cdn.jsdelivr.net/npm/world-countries@5.1.0/countries.json"
URL_UNESCO = (
    "https://data.unesco.org/api/explore/v2.1/catalog/"
    "datasets/whc001/exports/json"
)

REGIONS = {
    "Africa": "Afrique",
    "Americas": "Amériques",
    "Asia": "Asie",
    "Europe": "Europe",
    "Oceania": "Océanie",
    "Antarctic": "Antarctique",
}


def charger_json(url):
    with urlopen(url, timeout=120) as reponse:
        return json.load(reponse)


# Réutiliser world-countries si le paquet est déjà installé dans React.
fichier_local = (
    DOSSIER_ML.parent / "frontend/node_modules/world-countries/countries.json"
)

if fichier_local.exists():
    pays_du_monde = json.loads(fichier_local.read_text(encoding="utf-8"))
else:
    pays_du_monde = charger_json(URL_PAYS)

from urllib.error import URLError

# Première tentative : données officielles de l’UNESCO.
try:
    sites_unesco = charger_json(URL_UNESCO)
    print("Patrimoine chargé depuis l’UNESCO.")

except (URLError, TimeoutError) as erreur:
    print(f"UNESCO inaccessible : {erreur}")
    print("Essai avec une liste de secours…")
    sites_unesco = []

    url_secours = (
        "https://raw.githubusercontent.com/brandondatasets/"
        "unesco-world-heritage-sites/"
        "ce6e2deff0c325b972514b3366d3ee94323c8ee9/country"
    )

    # Associer les noms anglais de la liste aux codes des pays.
    codes_par_nom = {}
    for pays in pays_du_monde:
        noms = [
            pays["name"]["common"],
            pays["name"]["official"],
            *pays.get("altSpellings", []),
        ]
        for nom in noms:
            codes_par_nom[nom.strip().casefold()] = pays["cca2"]

    try:
        with urlopen(url_secours, timeout=30) as reponse:
            contenu = reponse.read().decode("utf-8")

        code = None
        for ligne in contenu.splitlines():
            ligne = ligne.strip()
            if ligne.startswith("## "):
                code = codes_par_nom.get(ligne[3:].strip().casefold())
            elif ligne and code:
                sites_unesco.append({
                    "iso_codes": [code],
                    "name_fr": None,
                    "name_en": ligne,
                    "source": url_secours,
                })

        print(f"{len(sites_unesco)} entrées patrimoniales de secours chargées.")

    except (URLError, TimeoutError) as erreur_secours:
        print(f"Liste de secours inaccessible : {erreur_secours}")
        print("Création des fiches avec les données pays disponibles.")
DOSSIER_FICHES.mkdir(parents=True, exist_ok=True)

for pays in pays_du_monde:
    code = pays["cca2"]
    nom = pays["translations"]["fra"]["common"]
    nom_officiel = pays["translations"]["fra"]["official"]
    capitale = ", ".join(pays["capital"]) or "Non renseignée dans la source"
    region = REGIONS.get(pays["region"], pays["region"])

    lignes = [
        f"# {nom}",
        "",
        f"Nom anglais : {pays['name']['common']}. Code pays : {code}.",
        "",
        "## Présentation du pays",
        "",
        f"Nom officiel : {nom_officiel}.",
        f"Région du monde : {region}.",
        f"Capitale(s) : {capitale}.",
        "",
        "## Drapeau",
        "",
        f"{nom} : {pays['flag']}",
        "",
        "Source géographique : https://github.com/mledoze/countries",
        "",
        "## Patrimoine et lieux remarquables",
        "",
    ]

    lieux = sorted(
        (
            site for site in sites_unesco
            if code in (site["iso_codes"] or []) and not site.get("date_end")
        ),
        key=lambda site: site.get("name_fr") or site["name_en"],
    )

    for lieu in lieux:
        titre = lieu.get("name_fr") or lieu["name_en"]
        if lieu.get("id_no"):
            lien = f"https://whc.unesco.org/fr/list/{lieu['id_no']}/"
        else:
            lien = lieu["source"]        
        lignes.append(f"- {titre} — {lien}")

    if not lieux:
        lignes.append("Aucun site patrimonial renseigné dans les données disponibles.")
    chemin = DOSSIER_FICHES / f"{code}.md"
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")

print(f"{len(pays_du_monde)} fiches créées dans {DOSSIER_FICHES}")