from src.db import get_conn
from unidecode import unidecode

def slugify(text):
    text = unidecode(text.lower().strip())
    text = text.replace(" ", "-")
    return text

def main():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT neighborhood_id, name
        FROM neighborhood
        WHERE slug IS NULL OR slug = ''
    """)
    rows = cur.fetchall()

    for nid, name in rows:
        slug = slugify(name)
        cur.execute("""
            UPDATE neighborhood
            SET slug = %s
            WHERE neighborhood_id = %s
        """, (slug, nid))

    conn.commit()
    print(f"✅ Slugs generados para {len(rows)} barrios")

if __name__ == "__main__":
    main()
