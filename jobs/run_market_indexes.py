from src.db import get_conn
from src.aggregate import aggregate_market_indexes

if __name__ == "__main__":
    # use context managers to ensure connection/cursor cleanup
    with get_conn() as conn:
        aggregate_market_indexes(conn)
        with conn.cursor() as cur:
            # report how many weekly entries we have
            cur.execute("SELECT COUNT(*) FROM market_index_weekly")
            weeks = cur.fetchone()[0]
            print("Semanas en índice:", weeks)
    print("Agregación de índices de mercado completada")
