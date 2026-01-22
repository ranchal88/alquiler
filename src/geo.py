from unidecode import unidecode

def normalize(text):
    return unidecode(text.lower().strip())

def load_neighborhood_map(conn):
    """
    Devuelve dict: slug -> neighborhood_id
    """
    cur = conn.cursor()
    cur.execute("SELECT neighborhood_id, slug FROM neighborhood")
    rows = cur.fetchall()

    mapping = {slug: nid for nid, slug in rows}
    return mapping
