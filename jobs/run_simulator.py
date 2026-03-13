from src.db import get_conn
from src.simulatorv2 import simulate_rent_price_v2

conn = get_conn()

result = simulate_rent_price_v2(
    conn=conn,
    neighborhood_id=2,  # Trafalgar (ejemplo)
    square_meters=70
)

print(result)
