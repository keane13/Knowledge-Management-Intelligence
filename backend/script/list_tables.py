import psycopg2

try:
    conn = psycopg2.connect(
        dbname="rag_chat",
        user="postgres",
        password="admin",
        host="127.0.0.1",
        port="5432"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """)
    for table in cur.fetchall():
        print(table[0])
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
