def aggregate_week(conn, start_date, end_date):
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO zone_market_stats (
            zone_id, period_start, period_end, property_type,
            median_price_per_m2, p25_price_per_m2, p75_price_per_m2, sample_size
        )
        SELECT
            zn.zone_id,
            %s,
            %s,
            'flat',
            percentile_cont(0.5) WITHIN GROUP (ORDER BY ls.price_per_m2),
            percentile_cont(0.25) WITHIN GROUP (ORDER BY ls.price_per_m2),
            percentile_cont(0.75) WITHIN GROUP (ORDER BY ls.price_per_m2),
            COUNT(*)
        FROM listing_snapshot ls
        JOIN zone_neighborhood zn ON zn.neighborhood_id = ls.neighborhood_id
        WHERE ls.snapshot_date BETWEEN %s AND %s
          AND ls.property_type = 'flat'
        GROUP BY zn.zone_id
        ON CONFLICT (zone_id, period_start, property_type)
        DO UPDATE SET
            period_end = EXCLUDED.period_end,
            median_price_per_m2 = EXCLUDED.median_price_per_m2,
            p25_price_per_m2 = EXCLUDED.p25_price_per_m2,
            p75_price_per_m2 = EXCLUDED.p75_price_per_m2,
            sample_size = EXCLUDED.sample_size
    """, (start_date, end_date, start_date, end_date))

    conn.commit()
