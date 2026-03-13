from dataclasses import dataclass


@dataclass
class PriceSimulationResult:
    price_low: float
    price_mid: float
    price_high: float
    sample_size: int
    week_start: str
    confidence: str


def size_adjustment_factor(square_meters: float) -> float:
    """
    Ajuste no lineal €/m² por tamaño del piso.
    """
    if square_meters < 35:
        return 1.07
    elif square_meters < 50:
        return 1.04
    elif square_meters <= 80:
        return 1.00
    elif square_meters <= 120:
        return 0.96
    else:
        return 0.93


def simulate_rent_price_v2(
    conn,
    neighborhood_id: int,
    square_meters: float
) -> PriceSimulationResult:
    cur = conn.cursor()

    cur.execute("""
        SELECT
          week_start,
          sample_size,
          p25_price_per_m2,
          median_price_per_m2,
          p75_price_per_m2
        FROM neighborhood_market_weekly
        WHERE neighborhood_id = %s
        ORDER BY week_start DESC
        LIMIT 1
    """, (neighborhood_id,))

    row = cur.fetchone()

    if not row:
        raise ValueError("No hay datos suficientes para este barrio")

    week_start, sample_size, p25, median, p75 = row

    p25 = float(p25)
    median = float(median)
    p75 = float(p75)

    # Ajuste por tamaño
    size_factor = size_adjustment_factor(square_meters)

    price_low = p25 * square_meters * size_factor
    price_mid = median * square_meters * size_factor
    price_high = p75 * square_meters * size_factor

    # Penalización por baja muestra
    if sample_size < 120:
        price_low *= 0.95
        price_high *= 1.05
        confidence = "media"
    elif sample_size < 250:
        confidence = "alta"
    else:
        confidence = "muy alta"

    return PriceSimulationResult(
        price_low=round(price_low, 0),
        price_mid=round(price_mid, 0),
        price_high=round(price_high, 0),
        sample_size=sample_size,
        week_start=str(week_start),
        confidence=confidence
    )
