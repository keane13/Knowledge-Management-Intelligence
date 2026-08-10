import os
import sys

# Set it BEFORE anything else
os.environ["PHOENIX_WORKING_DIR"] = os.path.join(os.getcwd(), "test_px_data")
os.makedirs(os.environ["PHOENIX_WORKING_DIR"], exist_ok=True)

import phoenix as px
print(f"Phoenix version: {px.__version__}")
print(f"PHOENIX_WORKING_DIR in environ: {os.environ.get('PHOENIX_WORKING_DIR')}")

try:
    session = px.launch_app()
    print(f"Session URL: {session.url}")
    # Check where the DB is
    # In newer versions, sessions have information about the database
except Exception as e:
    print(f"Error launching Phoenix: {e}")
finally:
    # Cleanup? Maybe not yet
    pass
