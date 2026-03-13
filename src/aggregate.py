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


def aggregate_market_indexes(conn):
    cur = conn.cursor()

    cur.execute("""
        WITH madrid AS (
            SELECT
                week_start,
                ROUND(SUM(median_price_per_m2 * sample_size) / SUM(sample_size), 2) AS madrid_index,
                SUM(sample_size) AS total_sample_size
            FROM neighborhood_market_weekly
            GROUP BY week_start
        ),
        premium AS (
            SELECT
                week_start,
                ROUND(SUM(median_price_per_m2 * sample_size) / SUM(sample_size), 2) AS premium_index,
                SUM(sample_size) AS premium_sample_size
            FROM neighborhood_market_weekly
            WHERE neighborhood_id IN (
                SELECT neighborhood_id
                FROM neighborhood
                WHERE name IN ('Recoletos', 'Trafalgar', 'Chueca-Justicia', 'Lista', 'Almagro', 'Goya')
            )
            GROUP BY week_start
        ),
        popular AS (
            SELECT
                week_start,
                ROUND(SUM(median_price_per_m2 * sample_size) / SUM(sample_size), 2) AS popular_index,
                SUM(sample_size) AS popular_sample_size
            FROM neighborhood_market_weekly
            WHERE neighborhood_id IN (
                SELECT neighborhood_id
                FROM neighborhood
                WHERE name IN ('Ríos Rosas', 'Cuatro Caminos', 'Lavapiés-Embajadores', 'Delicias')
            )
            GROUP BY week_start
        )
        INSERT INTO public.market_index_weekly (
            week_start,
            madrid_index,
            premium_index,
            popular_index,
            spread_premium_popular,
            total_sample_size,
            premium_sample_size,
            popular_sample_size
        )
        SELECT
            m.week_start,
            m.madrid_index,
            p.premium_index,
            po.popular_index,
            ROUND(p.premium_index - po.popular_index, 2) AS spread_premium_popular,
            m.total_sample_size,
            p.premium_sample_size,
            po.popular_sample_size
        FROM madrid m
        JOIN premium p ON p.week_start = m.week_start
        JOIN popular po ON po.week_start = m.week_start
        ON CONFLICT (week_start)
        DO UPDATE SET
            madrid_index = EXCLUDED.madrid_index,
            premium_index = EXCLUDED.premium_index,
            popular_index = EXCLUDED.popular_index,
            spread_premium_popular = EXCLUDED.spread_premium_popular,
            total_sample_size = EXCLUDED.total_sample_size,
            premium_sample_size = EXCLUDED.premium_sample_size,
            popular_sample_size = EXCLUDED.popular_sample_size;
    """)

    conn.commit()