import requests

base_url = "http://localhost:8000"

print("Registering users...")
user1 = {"username": "alice", "password": "password123"}
r1 = requests.post(f"{base_url}/register", json=user1)
print(f"Register Alice: {r1.status_code} - {r1.text}")

user2 = {"username": "bob", "password": "secure456"}
r2 = requests.post(f"{base_url}/register", json=user2)
print(f"Register Bob: {r2.status_code} - {r2.text}")

# Test duplicate
r3 = requests.post(f"{base_url}/register", json=user1)
print(f"Register Duplicate: {r3.status_code} - {r3.text}")

print("\nLogging in...")
l1 = requests.post(f"{base_url}/login", json=user1)
print(f"Login Alice (correct): {l1.status_code} - {l1.text}")

user1_wrong = {"username": "alice", "password": "wrongpassword"}
l2 = requests.post(f"{base_url}/login", json=user1_wrong)
print(f"Login Alice (wrong): {l2.status_code} - {l2.text}")
