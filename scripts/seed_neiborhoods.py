from src.db import get_conn

DISTRICTS = {
    "Chamberí": [
        "Trafalgar",
        "Almagro",
        "Ríos Rosas",
        "Vallehermoso"
    ],
    "Salamanca": [
        "Goya",
        "Lista",
        "Recoletos",
        "Castellana",
        "Fuente del Berro"
    ],
    "Arganzuela": [
        "Delicias",
        "Acacias",
        "Palos de Moguer",
        "Legazpi"
    ]
}

def seed():
    conn = get_conn()
    cur = conn.cursor()

    for district, neighborhoods in DISTRICTS.items():
        cur.execute(
            "INSERT INTO district (name) VALUES (%s) ON CONFLICT DO NOTHING RETURNING district_id",
            (district,)
        )
        row = cur.fetchone()
        if row:
            district_id = row[0]
        else:
            cur.execute("SELECT district_id FROM district WHERE name = %s", (district,))
            district_id = cur.fetchone()[0]

        for n in neighborhoods:
            cur.execute("""
                INSERT INTO neighborhood (district_id, name)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, (district_id, n))

    conn.commit()
    print("✅ Distritos y barrios cargados")

if __name__ == "__main__":
    seed()
