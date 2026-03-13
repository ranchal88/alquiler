from src.db import get_conn
import pandas as pd
import matplotlib.pyplot as plt


def load_df(conn, query):
    return pd.read_sql(query, conn)


if __name__ == "__main__":

    conn = get_conn()

    madrid_query = """
    SELECT
      week_start,
      SUM(median_price_per_m2 * sample_size) / SUM(sample_size) AS madrid_index
    FROM neighborhood_market_weekly
    GROUP BY week_start
    ORDER BY week_start
    """

    premium_popular_query = """
    WITH premium AS (
      SELECT
        week_start,
        SUM(median_price_per_m2 * sample_size) / SUM(sample_size) AS premium_idx
      FROM neighborhood_market_weekly
      WHERE neighborhood_id IN (
        SELECT neighborhood_id
        FROM neighborhood
        WHERE name IN ('Recoletos','Trafalgar','Chueca-Justicia','Lista','Almagro','Goya')
      )
      GROUP BY week_start
    ),
    popular AS (
      SELECT
        week_start,
        SUM(median_price_per_m2 * sample_size) / SUM(sample_size) AS popular_idx
      FROM neighborhood_market_weekly
      WHERE neighborhood_id IN (
        SELECT neighborhood_id
        FROM neighborhood
        WHERE name IN ('Ríos Rosas','Cuatro Caminos','Lavapiés-Embajadores','Delicias')
      )
      GROUP BY week_start
    )
    SELECT
      p.week_start,
      p.premium_idx,
      po.popular_idx,
      p.premium_idx - po.popular_idx AS spread
    FROM premium p
    JOIN popular po ON p.week_start = po.week_start
    ORDER BY p.week_start
    """

    df_madrid = load_df(conn, madrid_query)
    df_seg = load_df(conn, premium_popular_query)

    df_madrid["week_start"] = pd.to_datetime(df_madrid["week_start"])
    df_seg["week_start"] = pd.to_datetime(df_seg["week_start"])

    # Madrid Index
    plt.figure()
    plt.plot(df_madrid["week_start"], df_madrid["madrid_index"], marker="o")
    plt.title("Madrid Rent Index")
    plt.xlabel("Semana")
    plt.ylabel("€/m²")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # Premium vs Popular
    plt.figure()
    plt.plot(df_seg["week_start"], df_seg["premium_idx"], marker="o", label="Premium")
    plt.plot(df_seg["week_start"], df_seg["popular_idx"], marker="o", label="Popular")
    plt.title("Premium vs Popular Rent Index")
    plt.xlabel("Semana")
    plt.ylabel("€/m²")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # Spread
    plt.figure()
    plt.plot(df_seg["week_start"], df_seg["spread"], marker="o")
    plt.title("Premium - Popular Spread")
    plt.xlabel("Semana")
    plt.ylabel("€/m²")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()