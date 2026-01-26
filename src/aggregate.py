def aggregate_week_neighborhood(conn, start_date, end_date):
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO neighborhood_market_weekly (
            neighborhood_id,
            week_start,
            sample_size,
            p25_price_per_m2,
            median_price_per_m2,
            p75_price_per_m2,
            min_price_per_m2,
            max_price_per_m2
        )
        SELECT
            ls.neighborhood_id,
            %s AS week_start,
            COUNT(*) AS sample_size,
            percentile_cont(0.25) WITHIN GROUP (ORDER BY ls.price_per_m2),
            percentile_cont(0.5)  WITHIN GROUP (ORDER BY ls.price_per_m2),
            percentile_cont(0.75) WITHIN GROUP (ORDER BY ls.price_per_m2),
            MIN(ls.price_per_m2),
            MAX(ls.price_per_m2)
        FROM listing_snapshot ls
        WHERE ls.snapshot_date BETWEEN %s AND %s
          AND ls.property_type = 'flat'
        GROUP BY ls.neighborhood_id
        ON CONFLICT (neighborhood_id, week_start)
        DO UPDATE SET
            sample_size = EXCLUDED.sample_size,
            p25_price_per_m2 = EXCLUDED.p25_price_per_m2,
            median_price_per_m2 = EXCLUDED.median_price_per_m2,
            p75_price_per_m2 = EXCLUDED.p75_price_per_m2,
            min_price_per_m2 = EXCLUDED.min_price_per_m2,
            max_price_per_m2 = EXCLUDED.max_price_per_m2;
    """, (start_date, start_date, end_date))

    conn.commit()
