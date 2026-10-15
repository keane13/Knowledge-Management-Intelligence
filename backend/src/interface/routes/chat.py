import time
import json
import uuid
import asyncio
import os
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

from src.infrastructure.auth import get_current_user
from src.domain.security.guard import guard_input, GuardrailException
from src.application.rag.pipeline import run_rag, run_rag_async
from src.application.nlq.handle_chat import _detect_intent, HandleChatUseCase
from google.adk.sessions import InMemorySessionService
from src.interface.rate_limiter import limiter
from src.infrastructure.llm.timeouts import with_heartbeat

router = APIRouter(tags=["Chat"])

# Valid modes
ASYNC_MODES = {"reasoning", "deep_analytic"}
SYNC_MODES  = {"fast", "summarize", "thinking"}


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    mode: str = "fast"
    selected_files: Optional[List[str]] = None
    use_ollama: bool = False


def get_session_owner(session_id):
    """Returns (exists, user_id) for a chat session."""
    from src.infrastructure.firestore_client import get_firestore_client
    doc = get_firestore_client().collection("chat_sessions").document(session_id).get()
    if not doc.exists:
        return False, None
    return True, doc.to_dict().get("user_id")


def save_message(session_id, role, content, sources=None, user_id=None):
    try:
        from src.infrastructure.firestore_client import get_firestore_client
        import datetime
        import uuid
        
        db = get_firestore_client()
        session_ref = db.collection("chat_sessions").document(session_id)
        session_doc = session_ref.get()
        
        title = "New Chat"
        if not session_doc.exists:
            if role == "user":
                title = content[:30] + "..." if len(content) > 30 else content
            session_ref.set({
                "id": session_id,
                "user_id": user_id,
                "title": title,
                "timestamp": datetime.datetime.now(datetime.timezone.utc)
            })
        else:
            if session_doc.to_dict().get("user_id") != user_id:
                print(f"Refusing to write to session {session_id}: not owned by {user_id}")
                return
            if role == "user":
                data = session_doc.to_dict()
                # Initialize title if it was a default "New Chat" and we get a user message
                if data.get("title") == "New Chat":
                    title = content[:30] + "..." if len(content) > 30 else content
                    session_ref.update({
                        "title": title,
                        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                    })
                else:
                    session_ref.update({
                        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                    })
            else:
                session_ref.update({
                    "timestamp": datetime.datetime.now(datetime.timezone.utc)
                })
                
        message_id = str(uuid.uuid4())
        session_ref.collection("messages").document(message_id).set({
            "id": message_id,
            "role": role,
            "content": content,
            "sources": sources, # dicts/lists are natively supported in Firestore
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        })
    except Exception as e:
        print(f"Failed to save message to Firestore: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# SSE STREAM HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

class StreamHandler:

    # ── Cached Response ──────────────────────────────────────────────────────
    @staticmethod
    async def cached_event_generator(session_id: str, question: str, start_time: float, cached_data: dict, mode: str, user_id: str):
        yield f"event: session_id\ndata: {session_id}\n\n"
        
        full_answer = cached_data.get("content", "")
        citation_sources = cached_data.get("sources", [{"filename": "Semantic Cache (Hit)", "content": "Loaded from cache"}])
        
        import asyncio
        words = full_answer.split(" ")
        for i, w in enumerate(words):
            yield f"event: token\ndata: {json.dumps(w + (' ' if i < len(words)-1 else ''))}\n\n"
            await asyncio.sleep(0.03)  # Diperlambat agar lebih natural
            
        yield f"event: citation\ndata: {json.dumps({'sources': citation_sources, 'mode': mode})}\n\n"
        
        total_latency = round(time.time() - start_time, 4)
        final_metrics = {"latency": total_latency, "proc_latency": 0.0}
        yield f"event: metrics\ndata: {json.dumps(final_metrics)}\n\n"
        yield f"event: message_complete\ndata: {json.dumps({'sources': citation_sources})}\n\n"
        yield "event: done\ndata: [DONE]\n\n"
        
        await asyncio.to_thread(save_message, session_id, "assistant", full_answer, citation_sources, user_id)

    # ── NLQ (Data Query) ─────────────────────────────────────────────────────
    @staticmethod
    async def nlq_event_generator(session_id: str, question: str, start_time: float, user_id: str):
        yield f"event: session_id\ndata: {session_id}\n\n"
        metrics_init = {"latency": 0.0, "status": "processing_complete"}
        yield f"event: metrics\ndata: {json.dumps(metrics_init)}\n\n"

        mem_service = InMemorySessionService()
        await mem_service.create_session(app_name="rag_pro_nlq", user_id="user", session_id=session_id)

        use_case = HandleChatUseCase(persistence_service=mem_service)
        full_answer = ""
        async for evt in use_case.execute(session_id, "user", question):
            if evt["type"] == "chunk":
                full_answer += evt["content"]
                yield f"event: token\ndata: {json.dumps(evt['content'])}\n\n"
            elif evt["type"] == "chart_config":
                yield f"event: chart_config\ndata: {json.dumps(evt)}\n\n"
            elif evt["type"] == "sql":
                yield f"event: sql\ndata: {json.dumps(evt)}\n\n"
            elif evt["type"] == "error":
                yield f"event: error\ndata: {json.dumps({'detail': evt['detail']})}\n\n"
                yield "event: done\ndata: [DONE]\n\n"
                return

        total_latency = round(time.time() - start_time, 4)
        final_metrics = {"latency": total_latency, "proc_latency": 0.0}
        yield f"event: metrics\ndata: {json.dumps(final_metrics)}\n\n"

        # Citation untuk NLQ
        nlq_citation = [{"filename": "BigQuery (NLQ)", "content": "Generated by Data Agent"}]
        yield f"event: citation\ndata: {json.dumps({'sources': nlq_citation, 'mode': 'nlq'})}\n\n"

        yield "event: done\ndata: [DONE]\n\n"

        await asyncio.to_thread(save_message, session_id, "assistant", full_answer,
                                [{"filename": "BigQuery (NLQ)", "content": "Generated by Data Agent"}], user_id)

    # ── RAG Standard (fast / summarize / thinking) ────────────────────────────────────
    @staticmethod
    async def rag_event_generator(session_id: str, question: str, mode: str, selected_files: list, start_time: float, use_ollama: bool, user_id: str):
        yield f"event: session_id\ndata: {session_id}\n\n"

        actual_model_key = "gemini-flash-lite-latest"
        if use_ollama:
            actual_model_key = "ollama-local"
        
        try:
            from src.application.rag.pipeline import run_rag_stream_events
            
            trace_data = None
            async for event in run_rag_stream_events(
                question,
                selected_files=selected_files,
                mode=mode,
                stream=True,
                model_key=actual_model_key
            ):
                etype = event.get("type")
                if etype == "thinking_step":
                    thinking_data = {
                        "step":    event.get("step", "thinking"),
                        "content": event.get("content", ""),
                    }
                    yield f"event: thinking_step\ndata: {json.dumps(thinking_data)}\n\n"
                    await asyncio.sleep(0.01)
                elif etype == "done":
                    trace_data = event.get("trace_data")

            citation_sources = trace_data.get("citation", [])
            messages = trace_data.get("messages_for_stream")
            model_key_resolved = trace_data.get("actual_model_key_resolved")

            if not messages:
                yield f"event: error\ndata: {json.dumps({'detail': 'Pipeline tidak menghasilkan messages'})}\n\n"
                return

            # ✅ Stream LLM response langsung, iterasi sync stream via run_in_executor
            from src.infrastructure.llm.llm import generate_answer
            yield "event: message_start\ndata: {}\n\n"
            full_answer = ""

            loop = asyncio.get_event_loop()
            sync_stream = await loop.run_in_executor(
                None,
                lambda: generate_answer(messages, stream=True, model_key=model_key_resolved)
            )

            # Iterasi chunk satu per satu via executor agar tidak blocking
            def get_next_chunk(iterator):
                try:
                    return next(iterator)
                except StopIteration:
                    return None

            stream_iter = iter(sync_stream)
            while True:
                chunk = await loop.run_in_executor(None, get_next_chunk, stream_iter)
                if chunk is None:
                    break
                content = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
                if content:
                    full_answer += content
                    yield f"event: token\ndata: {json.dumps(content)}\n\n"

            await asyncio.to_thread(save_message, session_id, "assistant", full_answer, citation_sources, user_id)
            if not selected_files and full_answer.strip():
                try:
                    from src.infrastructure.persistence.semantic_cache import set_semantic_cache
                    from src.application.nlq.handle_chat import get_gemini_encoder
                    await asyncio.to_thread(
                        set_semantic_cache, 
                        question, 
                        {"content": full_answer, "sources": citation_sources}, 
                        get_gemini_encoder(),
                        f"rag:{mode}"
                    )
                except Exception as e:
                    print(f"Failed to cache RAG response: {e}")

            # Emit citation
            yield f"event: citation\ndata: {json.dumps({'sources': citation_sources, 'mode': mode})}\n\n"
            
            # Emit metrics (latency)
            total_latency = round(time.time() - start_time, 4)
            final_metrics = {"latency": total_latency, "proc_latency": 0.0}
            yield f"event: metrics\ndata: {json.dumps(final_metrics)}\n\n"

            # Emit completion and done
            yield f"event: message_complete\ndata: {json.dumps({'sources': citation_sources})}\n\n"
            yield "event: done\ndata: [DONE]\n\n"

        except GuardrailException as e:
            yield f"event: error\ndata: {json.dumps({'detail': str(e)})}\n\n"
        except Exception as e:
            print(f"Error in rag stream: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': 'Internal error occur'})}\n\n"

    # ── Async Agentic (reasoning / deep_analytic) ─────────────────────────────
    @staticmethod
    async def async_rag_event_generator(session_id: str, question: str, mode: str, selected_files: list, start_time: float, use_ollama: bool, user_id: str):
        yield f"event: session_id\ndata: {session_id}\n\n"

        actual_model_key = "gemini-flash-lite-latest"
        if use_ollama:
            actual_model_key = "ollama-reasoning"
            
        full_answer = ""
        citation_sources = []

        try:
            async for event in run_rag_async(question, selected_files=selected_files, mode=mode, model_key=actual_model_key):
                etype = event.get("type")

                if etype == "thinking_step":
                    thinking_data = {
                        "step":    event.get("step", "thinking"),
                        "content": event.get("content", ""),
                    }
                    yield f"event: thinking_step\ndata: {json.dumps(thinking_data)}\n\n"

                elif etype == "chunk":
                    content = event.get("content", "")
                    full_answer += content
                    yield f"event: token\ndata: {json.dumps(content)}\n\n"

                elif etype == "citation":
                    citation_sources = event.get("sources", [])
                    yield f"event: citation\ndata: {json.dumps({'sources': citation_sources, 'mode': mode})}\n\n"
        except Exception as e:
            print(f"Error in async rag stream: {e}")
            yield f"event: error\ndata: {json.dumps({'detail': 'Internal error occur'})}\n\n"
            yield "event: done\ndata: [DONE]\n\n"
            return

        total_latency = round(time.time() - start_time, 4)
        final_metrics = {"latency": total_latency, "proc_latency": 0.0}
        yield f"event: metrics\ndata: {json.dumps(final_metrics)}\n\n"
        yield "event: done\ndata: [DONE]\n\n"

        await asyncio.to_thread(save_message, session_id, "assistant", full_answer, citation_sources, user_id)
        if not selected_files and full_answer.strip():
            try:
                from src.infrastructure.persistence.semantic_cache import set_semantic_cache
                from src.application.nlq.handle_chat import get_gemini_encoder
                await asyncio.to_thread(
                    set_semantic_cache, 
                    question, 
                    {"content": full_answer, "sources": citation_sources}, 
                    get_gemini_encoder(),
                    f"rag:{mode}"
                )
            except Exception as e:
                print(f"Failed to cache async RAG response: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/chat")
@limiter.limit("10/minute")
async def chat_endpoint(request: Request, body: ChatRequest, current_user: str = Depends(get_current_user)):
    question      = body.question
    session_id    = body.session_id
    
    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        try:
            exists, owner = await asyncio.to_thread(get_session_owner, session_id)
        except Exception as e:
            print(f"Session ownership check failed: {e}")
            raise HTTPException(status_code=503, detail="Chat history unavailable")
        if exists and owner != current_user:
            raise HTTPException(status_code=404, detail="Session not found")

    try:
        question = await guard_input(question)
    except GuardrailException as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Simpan pesan user di thread terpisah (non-blocking)
    asyncio.create_task(asyncio.to_thread(save_message, session_id, "user", question, None, current_user))

    # ── Route: NLQ (Data Query) ───────────────────────────────────────────────
    # Jalankan intent detection di thread agar tidak block event loop
    intent = await asyncio.to_thread(_detect_intent, question)
    start_time = time.time()
    
    if intent == "Data Query":
        generator = StreamHandler.nlq_event_generator(session_id, question, start_time, current_user)
    
    # ── Route: Async Agentic Modes ────────────────────────────────────────────
    else:
        # Check cache only for RAG
        cached = None
        if not body.selected_files:
            try:
                from src.infrastructure.persistence.semantic_cache import get_semantic_match
                from src.application.nlq.handle_chat import get_gemini_encoder
                cached = await asyncio.to_thread(get_semantic_match, question, get_gemini_encoder(), f"rag:{body.mode}")
            except Exception as e:
                print(f"Cache lookup failed: {e}")
                
        if cached:
            generator = StreamHandler.cached_event_generator(session_id, question, start_time, cached, body.mode, current_user)
        elif body.mode in ASYNC_MODES:
            generator = StreamHandler.async_rag_event_generator(
                session_id, question, body.mode, body.selected_files, start_time, body.use_ollama, current_user
            )
        else:
            generator = StreamHandler.rag_event_generator(
                session_id, question, body.mode, body.selected_files, start_time, body.use_ollama, current_user
            )

    # Heartbeat comments keep proxies (Cloudflare closes idle connections after 100s) from
    # dropping the stream while a slow step (reasoning, NLQ agents) produces no events.
    return StreamingResponse(with_heartbeat(generator), media_type="text/event-stream")
