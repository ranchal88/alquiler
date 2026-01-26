from datetime import date, timedelta
from src.db import get_conn
from src.aggregate import aggregate_week_neighborhood

if __name__ == "__main__":
    conn = get_conn()

    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=6)

    aggregate_week_neighborhood(conn, start, end)
    print("Agregación semanal completada")
