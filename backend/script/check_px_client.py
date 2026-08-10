import phoenix as px
try:
    client = px.Client(endpoint="http://localhost:6006")
    df = client.get_spans_dataframe()
    if df is not None:
        print("Columns:", list(df.columns))
        token_cols = [c for c in df.columns if 'token' in c.lower()]
        print("Token Cols:", token_cols)
        if token_cols:
            print(df[token_cols].sum())
    else:
        print("No spans")
except Exception as e:
    print("Error:", e)
