import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect("phoenix_data/phoenix.db")
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = pd.read_sql_query(query, conn)
    print("Tables:", list(tables['name']))
    
    if "spans" in list(tables['name']):
        spans = pd.read_sql_query("SELECT * FROM spans LIMIT 1", conn)
        print("Span columns:", list(spans.columns))
        # look for token related columns
        token_cols = [c for c in spans.columns if 'token' in c.lower()]
        print("Token columns:", token_cols)
        
        # Or look in attributes json if it exists
        if 'attributes' in spans.columns:
            print("Attributes sample:", spans['attributes'].iloc[0])
except Exception as e:
    print("Error:", e)
