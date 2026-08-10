import os
import shutil
import tempfile
import glob

# We now store Phoenix DB cleanly in the project root's phoenix_data folder
db_dir = os.path.join(os.path.dirname(__file__), "phoenix_data")
print(f"Target DB dir is {db_dir}")

for p in glob.glob(os.path.join(db_dir, "*")):
    print(f"Found file: {p}")
    try:
        os.remove(p)
        print("Deleted file")
    except Exception as e:
        print(f"Could not delete {p}: {e}")

