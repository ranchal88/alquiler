def validate_today_snapshot(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) 
        FROM listing_snapshot
        WHERE snapshot_date = CURRENT_DATE
          AND (square_meters < 20 OR square_meters > 400
               OR price_per_m2 < 8 OR price_per_m2 > 45)
    """)
    bad = cur.fetchone()[0]

    if bad > 0:
        raise ValueError(f"Validación fallida: {bad} registros fuera de rango")
