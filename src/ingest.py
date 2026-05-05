from datetime import date
import hashlib

def fingerprint_listing(price, m2, rooms, neighborhood_id):
    raw = f"{price}-{m2}-{rooms}-{neighborhood_id}"
    return hashlib.sha256(raw.encode()).hexdigest()

from psycopg2 import OperationalError, InterfaceError
from src.db import get_conn


def ingest_listings(conn, listings, neighborhood_map, source, max_retries: int = 1):
    """
    listings: iterable de dicts normalizados

    Este método hace un solo `commit()` al final de la llamada. Si la
    conexión se pierde en medio del bucle (OperationalError) se cierra la
    conexión y, si quedan reintentos, se vuelve a llamar recursivamente con
    una nueva conexión. La clausula `ON CONFLICT DO NOTHING` garantiza que
    no haya duplicados en caso de volver a intentar el mismo lote.
    """

    cur = conn.cursor()
    try:
        # Crear data_run
        cur.execute(
            "INSERT INTO data_run (source, records_ingested) VALUES (%s, 0) RETURNING run_id",
            (source,)
        )
        run_id = cur.fetchone()[0]

        inserted = 0
        today = date.today()

        for l in listings:
            if l["property_type"] != "flat":
                continue

            neighborhood_key = l["neighborhood"]

            if neighborhood_key not in neighborhood_map:
                continue

            neighborhood_id = neighborhood_map[neighborhood_key]

            price = l["price_total"]
            m2 = l["square_meters"]
            rooms = l.get("rooms")

            if m2 <= 0 or price <= 0:
                continue

            price_m2 = price / m2
            if not (8 <= price_m2 <= 45):
                continue

            fp = fingerprint_listing(price, m2, rooms, neighborhood_id)

            try:
                cur.execute("""
                    INSERT INTO listing_snapshot (
                        snapshot_date, neighborhood_id,
                        price_total, square_meters, price_per_m2,
                        rooms, property_type, condition, source, fingerprint
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                """, (
                    today,
                    neighborhood_id,
                    price,
                    m2,
                    price_m2,
                    rooms,
                    "flat",
                    l.get("condition"),
                    source,
                    fp
                ))
                inserted += cur.rowcount
            except Exception as e:
                # cualquier excepción no-operacional la dejamos subir
                conn.rollback()
                raise e

        # Actualizar data_run
        cur.execute(
            "UPDATE data_run SET records_ingested = %s WHERE run_id = %s",
            (inserted, run_id)
        )

        conn.commit()
        return inserted

    except (OperationalError, InterfaceError):
        # No cerramos la conexión aquí. el llamador decide reconectar.
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
