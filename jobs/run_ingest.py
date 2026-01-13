from src.db import get_conn
from src.geo import load_neighborhood_map
from src.ingest import ingest_listings
from src.validate import validate_today_snapshot
from src.extractors.idealista.extractor import extract_trafalgar

if __name__ == "__main__":
    conn = get_conn()
    neighborhood_map = load_neighborhood_map(conn)

    listings = extract_trafalgar(pages=3)

    print(f"Extraídos: {len(listings)}")
    print(listings[:3])  # sanity check

    inserted = ingest_listings(
        conn,
        listings,
        neighborhood_map,
        source="idealista"
    )

    validate_today_snapshot(conn)
    print(f"Ingestados en DB: {inserted}")
