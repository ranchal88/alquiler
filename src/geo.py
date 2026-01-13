from unidecode import unidecode

def normalize(text):
    return unidecode(text.lower().strip())

def load_neighborhood_map(conn):
    """
    Devuelve dict: normalized_name -> neighborhood_id
    """
    cur = conn.cursor()
    cur.execute("SELECT neighborhood_id, name FROM neighborhood")
    rows = cur.fetchall()

    mapping = {}
    for nid, name in rows:
        mapping[normalize(name)] = nid

    return mapping
