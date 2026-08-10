import requests
import json
import os

try:
    print("Testing GET http://localhost:8000/files...")
    response = requests.get("http://localhost:8000/files")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.json()}")
    
    print("\nVerifying Local Directory...")
    docs_path = "data/docs"
    abs_path = os.path.abspath(docs_path)
    print(f"Checking path: {abs_path}")
    if os.path.exists(docs_path):
        print(f"Files found: {os.listdir(docs_path)}")
    else:
        print("Directory data/docs NOT found!")
        
except Exception as e:
    print(f"Error: {e}")
