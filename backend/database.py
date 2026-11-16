import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Cherche le fichier .env dans le même dossier que database.py.
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH, interpolate=False)


def get_connection():
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        connect_timeout=5,
    )