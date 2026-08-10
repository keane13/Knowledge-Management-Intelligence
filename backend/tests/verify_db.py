import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from src.infrastructure.database import init_db, SessionLocal, ChatSession, ChatMessage
import uuid
import datetime

def test_db():
    print("Testing Database connection and models...")
    try:
        # Initialize the database
        init_db()
        print("Database initialized successfully.")
        
        db = SessionLocal()
        
        # 1. Create a session
        session_id = str(uuid.uuid4())
        new_session = ChatSession(id=session_id, title="Test Session")
        db.add(new_session)
        db.commit()
        print(f"Created session: {session_id}")
        
        # 2. Add a message
        user_msg = ChatMessage(session_id=session_id, role="user", content="Hello DB")
        db.add(user_msg)
        db.commit()
        print("Added user message.")
        
        # 3. Retrieve session and messages
        retrieved_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        print(f"Retrieved session title: {retrieved_session.title}")
        print(f"Number of messages: {len(retrieved_session.messages)}")
        
        # 4. Cleanup
        db.delete(retrieved_session)
        db.commit()
        print("Cleaned up test data.")
        
        db.close()
        print("Database test passed!")
        
    except Exception as e:
        print(f"Error during database test: {e}")
        print("\nMake sure your PostgreSQL server is running and credentials in .env.local are correct.")

if __name__ == "__main__":
    test_db()
