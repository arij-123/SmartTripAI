import logging
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from dotenv import load_dotenv


load_dotenv(
    Path(__file__).resolve().parent / ".env",
    interpolate=False,
)

logger = logging.getLogger(__name__)

# Cache des photos trouvées pour éviter de répéter les appels.
cache_photos = {}


def lien_attribution(url):
    parties = urlsplit(url)
    parametres = dict(parse_qsl(parties.query))
    parametres.update({
        "utm_source": "smarttripai",
        "utm_medium": "referral",
    })

    return urlunsplit((
        parties.scheme,
        parties.netloc,
        parties.path,
        urlencode(parametres),
        parties.fragment,
    ))


def obtenir_photo_ville(ville, pays):
    cle_cache = (ville.strip().lower(), pays.strip().lower())

    if cle_cache in cache_photos:
        return cache_photos[cle_cache]

    cle_api = os.getenv("UNSPLASH_ACCESS_KEY")

    if not cle_api:
        logger.warning("UNSPLASH_ACCESS_KEY absente du fichier .env")
        return None

    try:
        response = httpx.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": f"{ville} {pays} city travel",
                "per_page": 1,
                "orientation": "landscape",
            },
            headers={
                "Authorization": f"Client-ID {cle_api}",
            },
            timeout=5.0,
        )
        response.raise_for_status()

        photos = response.json().get("results", [])

        if not photos:
            return None

        photo = photos[0]

        resultat = {
            "image_url": photo["urls"]["regular"],
            "photographer": photo["user"]["name"],
            "photographer_url": lien_attribution(
                photo["user"]["links"]["html"]
            ),
            "unsplash_url": lien_attribution(
                photo["links"]["html"]
            ),
        }

        cache_photos[cle_cache] = resultat
        return resultat

    except httpx.HTTPStatusError as erreur:
        logger.warning(
            "Unsplash a répondu avec le statut %s",
            erreur.response.status_code,
        )
    except (httpx.RequestError, ValueError, KeyError, TypeError):
        logger.warning(
            "Photo indisponible pour %s, %s",
            ville,
            pays,
        )

    # Une panne des photos ne bloque pas les recommandations.
    return None