import psycopg2
import os
import socket
from urllib.parse import urlparse, quote
from dotenv import load_dotenv

load_dotenv()  # ← ESTA LÍNEA ES LA CLAVE

def _fix_database_url(url: str) -> str:
    """Repara credenciales si tienen caracteres especiales que rompen el DSN."""
    if "@" not in url:
        return url

    # solo intentamos en DSN con esquema
    if "://" not in url:
        return url

    scheme, rest = url.split("://", 1)
    # Busca la última @ para separar credenciales de host
    if "@" not in rest:
        return url

    creds, host_path = rest.rsplit("@", 1)
    if ":" not in creds:
        return url

    user, password = creds.split(":", 1)
    user_enc = quote(user, safe="")
    password_enc = quote(password, safe="")
    fixed = f"{scheme}://{user_enc}:{password_enc}@{host_path}"
    return fixed

def get_conn():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está definido en el entorno.")

    database_url = _fix_database_url(database_url)

    parsed = urlparse(database_url)
    if parsed.hostname:
        try:
            socket.gethostbyname(parsed.hostname)
        except socket.gaierror:
            raise RuntimeError(
                f"No se puede resolver el host de la DB: {parsed.hostname}. "
                "Revisa conexión DNS / NETWORK / DATABASE_URL."
            )

    return psycopg2.connect(
        database_url,
        connect_timeout=15,
        sslmode="require",
    )