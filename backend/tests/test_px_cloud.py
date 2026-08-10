import os
import phoenix as px
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")
api_key = os.getenv("PHOENIX_API_KEY")

def test_auth():
    try:
        # User specified endpoint
        client = px.Client(endpoint="https://app.phoenix.arize.com/s/simon-keane13")
        df = client.get_spans_dataframe()
        print(f"Success, df length = {len(df) if df is not None else 'None'}")
    except Exception as e:
        print(f"Failed -> {e}")

test_auth()
