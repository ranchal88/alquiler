import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()  # ← ESTA LÍNEA ES LA CLAVE

def get_conn():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        connect_timeout=15,
        sslmode="require",
    )