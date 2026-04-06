from src.db import get_conn
from src.geo import load_neighborhood_map
from src.ingest import ingest_listings
from src.validate import validate_today_snapshot
from src.extractors.idealista.extractor import extract_all_neighborhoods

if __name__ == "__main__":
    conn = get_conn()
    try:
        neighborhood_map = load_neighborhood_map(conn)

        listings = extract_all_neighborhoods(pages=3)

        print(f"Extraídos: {len(listings)}")
        print(listings[:3])  # sanity check

        # procesar en trozos pequeños para que no haya transacciones enormes
        inserted = 0
        batch_size = 500
        for start in range(0, len(listings), batch_size):
            chunk = listings[start : start + batch_size]
            try:
                inserted += ingest_listings(
                    conn,
                    chunk,
                    neighborhood_map,
                    source="idealista",
                    max_retries=2,
                )
            except Exception as e:
                # un fallo serio: intentar reconectar y repetir la misma chunk una vez
                print(f"Error al insertar lote, reconectando: {e}")
                try:
                    conn.close()
                except Exception:
                    pass
                conn = get_conn()
                neighborhood_map = load_neighborhood_map(conn)
                inserted += ingest_listings(
                    conn,
                    chunk,
                    neighborhood_map,
                    source="idealista",
                    max_retries=1,
                )
            # cada batch hace commit internamente

        validate_today_snapshot(conn)
        print(f"Ingestados en DB: {inserted}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
