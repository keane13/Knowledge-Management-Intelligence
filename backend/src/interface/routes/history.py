import json
from fastapi import APIRouter, HTTPException, Depends
import datetime
from src.infrastructure.auth import get_current_user
from src.infrastructure.firestore_client import get_firestore_client, user_docs_sorted
from google.cloud import firestore

router = APIRouter(tags=["History"])

@router.get("/history")
def list_history(current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        docs = user_docs_sorted(db.collection("chat_sessions"), current_user)
        
        sessions = []
        for doc in docs:
            data = doc.to_dict()
            sessions.append({
                "id": data.get("id", doc.id),
                "title": data.get("title", "New Chat"),
                "timestamp": data.get("timestamp").isoformat() if hasattr(data.get("timestamp"), "isoformat") else str(data.get("timestamp"))
            })
        return sessions
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
def get_session(session_id: str, current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        session_doc = db.collection("chat_sessions").document(session_id).get()
        if not session_doc.exists or session_doc.to_dict().get("user_id") != current_user:
            raise HTTPException(status_code=404, detail="Session not found")
            
        data = session_doc.to_dict()
        
        # Get messages
        msg_docs = db.collection("chat_sessions").document(session_id).collection("messages").order_by("timestamp").stream()
        messages = []
        for mdoc in msg_docs:
            m = mdoc.to_dict()
            messages.append({
                "role": m.get("role"),
                "content": m.get("content"),
                "timestamp": m.get("timestamp").isoformat() if hasattr(m.get("timestamp"), "isoformat") else str(m.get("timestamp")),
                "sources": m.get("sources")
            })
            
        return {
            "id": data.get("id", session_id),
            "title": data.get("title", "New Chat"),
            "timestamp": data.get("timestamp").isoformat() if hasattr(data.get("timestamp"), "isoformat") else str(data.get("timestamp")),
            "messages": messages
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/history/{session_id}")
def delete_session(session_id: str, current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        session_ref = db.collection("chat_sessions").document(session_id)
        
        session_doc = session_ref.get()
        if not session_doc.exists or session_doc.to_dict().get("user_id") != current_user:
            raise HTTPException(status_code=404, detail="Session not found")
            
        # Batch delete messages
        msg_docs = session_ref.collection("messages").stream()
        batch = db.batch()
        for doc in msg_docs:
            batch.delete(doc.reference)
        batch.delete(session_ref)
        batch.commit()
        
        return {"message": "Deleted"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
