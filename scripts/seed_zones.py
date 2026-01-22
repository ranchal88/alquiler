from src.db import get_conn

ZONES = {
    "Chamberí Centro": [
        "Trafalgar",
        "Almagro"
    ],
    "Salamanca Residencial": [
        "Goya",
        "Lista"
    ],
    "Arganzuela Central": [
        "Delicias",
        "Acacias"
    ]
}

def seed():
    conn = get_conn()
    cur = conn.cursor()

    for zone_name, neighborhoods in ZONES.items():
        cur.execute("""
            INSERT INTO zone (name, description)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            RETURNING zone_id
        """, (zone_name, f"Zona operativa {zone_name}"))
        row = cur.fetchone()
        if row:
            zone_id = row[0]
        else:
            cur.execute("SELECT zone_id FROM zone WHERE name = %s", (zone_name,))
            zone_id = cur.fetchone()[0]

        for n in neighborhoods:
            cur.execute("""
                SELECT neighborhood_id FROM neighborhood WHERE name = %s
            """, (n,))
            neighborhood_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO zone_neighborhood (zone_id, neighborhood_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (zone_id, neighborhood_id))

    conn.commit()
    print("✅ Zonas operativas cargadas")

if __name__ == "__main__":
    seed()
