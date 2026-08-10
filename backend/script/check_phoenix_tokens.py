import sqlite3
import pandas as pd
import json

try:
    conn = sqlite3.connect("phoenix_data/phoenix.db")
    spans = pd.read_sql_query("SELECT attributes FROM spans WHERE attributes LIKE '%token%'", conn)
    print(f"Found {len(spans)} spans with token data.")
    
    total_tokens = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    for _, row in spans.iterrows():
        try:
            attrs = json.loads(row['attributes'])
            pt = attrs.get('llm.usage.prompt_tokens', 0)
            ct = attrs.get('llm.usage.completion_tokens', 0)
            tt = attrs.get('llm.usage.total_tokens', 0)
            if not tt and (pt or ct):
                tt = pt + ct
            total_prompt_tokens += int(pt)
            total_completion_tokens += int(ct)
            total_tokens += int(tt)
        except Exception as e:
            pass
            
    print(f"Total Prompt: {total_prompt_tokens}")
    print(f"Total Completion: {total_completion_tokens}")
    print(f"Total Tokens: {total_tokens}")

except Exception as e:
    print("Error:", e)
