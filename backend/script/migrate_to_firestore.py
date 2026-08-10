import os
import psycopg2
import psycopg2.extras
from google.cloud import firestore
import datetime
import uuid

# Configuration
POSTGRES_DB = "rag_chat"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "admin"
POSTGRES_HOST = "127.0.0.1"
POSTGRES_PORT = "5432"

FIRESTORE_KEY_PATH = r"C:\Users\keane\Desktop\Portofolio\Top 5\rag_pro_v3\backend\data\firestore-key\smooth-reason-491707-f6-b520a2342766.json"
FIRESTORE_DB_NAME = "knowldege-mi"

def migrate():
    # 1. Connect to Firestore
    print("Connecting to Firestore...")
    db = firestore.Client.from_service_account_json(
        FIRESTORE_KEY_PATH,
        database=FIRESTORE_DB_NAME
    )
    
    # 2. Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # 3. Migrate Users
    print("Migrating Users...")
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    for row in users:
        user_data = dict(row)
        user_id = user_data.pop('id', str(uuid.uuid4()))
        db.collection("users").document(user_id).set(user_data)
    print(f"Migrated {len(users)} users.")

    # 4. Migrate Chat Sessions with updated schema
    print("Migrating Chat Sessions...")
    cur.execute("SELECT * FROM chat_sessions")
    sessions = cur.fetchall()
    for row in sessions:
        session_data = dict(row)
        session_id = session_data.pop('id', str(uuid.uuid4()))
        
        # Ensure timestamp exists
        if not session_data.get("timestamp"):
            session_data["timestamp"] = datetime.datetime.utcnow()
            
        # Add requested fields
        session_data["citation"] = []
        session_data["mode"] = "standard"
        session_data["selected_sources"] = []
        
        db.collection("chat_sessions").document(session_id).set(session_data)
    print(f"Migrated {len(sessions)} chat sessions.")

    # 5. Migrate Chat Messages
    print("Migrating Chat Messages...")
    cur.execute("SELECT * FROM chat_messages")
    messages = cur.fetchall()
    for row in messages:
        msg_data = dict(row)
        msg_id = msg_data.pop('id', str(uuid.uuid4()))
        db.collection("chat_messages").document(msg_id).set(msg_data)
    print(f"Migrated {len(messages)} chat messages.")
    
    # 6. Seed Data Analysis History
    print("Seeding data_analysis_history...")
    db.collection("data_analysis_history").document("seed_doc").set({
        "timestamp": datetime.datetime.utcnow(),
        "query": "Sample initial analysis",
        "result": {},
        "user_id": "system"
    })
    
    # 7. Seed Report Builder History
    print("Seeding report_builder_history...")
    db.collection("report_builder_history").document("seed_doc").set({
        "timestamp": datetime.datetime.utcnow(),
        "report_title": "Sample Initial Report",
        "content": "This is a seed document.",
        "user_id": "system"
    })

    # 8. Seed Knowledge Base
    print("Seeding knowledge_base...")
    db.collection("knowledge_base").document("seed_doc").set({
        "file_name": "example_document.pdf",
        "size": 1024,
        "format_type": "pdf",
        "category": "general",
        "file_path": "/uploads/example_document.pdf",
        "selected": False,
        "timestamp": datetime.datetime.utcnow()
    })
    
    cur.close()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Error during migration: {e}")
