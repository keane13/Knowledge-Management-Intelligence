import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse

from src.infrastructure.auth import get_current_user
from google.adk.sessions import InMemorySessionService
from src.application.report.builder_pipeline import ReportBuilderUseCase
from src.infrastructure.llm.timeouts import with_heartbeat
from src.infrastructure.tools.mcp_toolbox import toolset
import datetime
import uuid
import traceback
from src.infrastructure.firestore_client import get_firestore_client, user_docs_sorted
from google.cloud import firestore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["Report Builder"])

@router.post("/build")
async def build_report(
    payload: dict = Body(...),
    current_user: str = Depends(get_current_user),
    # persistence = Depends(get_session_service)
):
    """
    Menjalankan Report Builder Multi-Agent Pipeline dan streaming progres/hasil ke frontend.
    """
    prompt = payload.get("prompt")
    session_id = payload.get("session_id", "default_report_session")

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt wajib diisi")

    text_model = "gemini-flash-lite-latest"

    use_case = ReportBuilderUseCase(persistence_service=InMemorySessionService(), text_model=text_model)

    async def event_generator() -> AsyncGenerator[str, None]:
        full_report_content = ""
        try:
            async for event in use_case.execute(session_id=session_id, user_id=current_user, prompt=prompt):
                if event.get("type") == "chunk":
                    full_report_content += event.get("content", "")
                
                if event.get("type") == "done":
                    # Save to Firestore
                    try:
                        db = get_firestore_client()
                        doc_id = str(uuid.uuid4())
                        doc_data = {
                            "id": doc_id,
                            "report_title": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                            "timestamp": datetime.datetime.utcnow(),
                            "content": full_report_content,
                            "user_id": current_user
                        }
                        db.collection("report_builder_history").document(doc_id).set(doc_data)
                    except Exception as e:
                        logger.error(f"Failed to save report history: {e}")

                # Stream the event as an SSE JSON
                data_str = json.dumps(event)
                yield f"data: {data_str}\n\n"
        except Exception as e:
            logger.exception("Report Builder Error")
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(with_heartbeat(event_generator()), media_type="text/event-stream")

@router.get("/history")
async def list_report_history(current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        docs = user_docs_sorted(db.collection("report_builder_history"), current_user)
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            history.append({
                "id": doc.id,
                "report_title": data.get("report_title", "Untitled Report"),
                "timestamp": data.get("timestamp").isoformat() if hasattr(data.get("timestamp"), "isoformat") else str(data.get("timestamp"))
            })
        return history
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{doc_id}")
async def get_report_history(doc_id: str, current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        doc = db.collection("report_builder_history").document(doc_id).get()
        if not doc.exists or doc.to_dict().get("user_id") != current_user:
            raise HTTPException(status_code=404, detail="History not found")
        data = doc.to_dict()
        if hasattr(data.get("timestamp"), "isoformat"):
            data["timestamp"] = data["timestamp"].isoformat()
        else:
             data["timestamp"] = str(data.get("timestamp"))
        return data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
