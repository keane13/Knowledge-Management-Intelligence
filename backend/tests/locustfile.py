from locust import HttpUser, task, between
import json

class ChatUser(HttpUser):
    # Waktu tunggu antara setiap request untuk mensimulasikan user asli (misal 1 - 3 detik)
    wait_time = between(1, 3)

    @task
    def test_chat_fast_mode(self):
        # Header yang sesuai dengan request ke backend
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer TEST_TOKEN_IF_ANY" # Sesuaikan jika endpoint di-auth
        }
        
        # Payload request untuk test mode Fast (menghindari RAG Reasoning yang berat)
        payload = {
            "query": "Halo, ini adalah test load.",
            "mode": "fast", 
            "selectedFiles": []
        }
        
        # Kirim request POST ke endpoint chat
        with self.client.post("/chat", json=payload, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Gagal dengan status {response.status_code}")

    @task(3) # Task ini dieksekusi 3x lebih sering dari task yang tidak memiliki bobot
    def test_get_documents(self):
        # Test endpoint yang sangat ringan (baca database statis)
        self.client.get("/documents")
