import os, json, sqlite3

CACHE_DB_PATH = "data/exact_cache.sqlite"
os.makedirs(os.path.dirname(CACHE_DB_PATH), exist_ok=True)

def get_db():
    c = sqlite3.connect(CACHE_DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS exact_cache "
              "(query TEXT PRIMARY KEY, data TEXT)")
    return c

def get_semantic_match(query: str, threshold: float = 0.98):
    # Fallback to exact match to save RAM / API calls
    try:
        with get_db() as c:
            cur = c.execute("SELECT data FROM exact_cache WHERE query = ?", (query.strip().lower(),))
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
    except Exception as e: 
        print(f"Cache lookup error: {e}")
    return None

def set_semantic_cache(query: str, data: dict):
    if len(query.strip()) < 10: return
    try:
        with get_db() as c:
            c.execute("INSERT OR REPLACE INTO exact_cache VALUES (?,?)",
                      (query.strip().lower(), json.dumps(data)))
            c.commit()
    except Exception as e: 
        print(f"Cache write error: {e}")
