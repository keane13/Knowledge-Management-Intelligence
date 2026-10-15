from typing import Dict, Any, AsyncGenerator
from opentelemetry import trace as otel_trace

from .vectorstore import get_vectorstore
from .retriever import retrieve
from .reranker import rerank
from src.infrastructure.llm.llm import generate_answer
from src.domain.prompt.prompt import build_prompt
from src.application.inference.latency import timer


def _get_tracer():
    """Lazily get the Phoenix OTel tracer (registered by monitoring.phoenix_setup)."""
    return otel_trace.get_tracer("rag_pro")



from typing import TypedDict, Optional, List, Dict, Any, Union
from langgraph.graph import StateGraph, END

class RagState(TypedDict):
    question: str
    selected_files: Optional[List[str]]
    mode: str
    stream: bool
    
    initial_docs: List[Any]
    ranked_docs: List[Any]
    
    trace_data: Dict[str, Any]
    actual_model_key: Optional[str]
    input_tokens: int
    
    answer: Any
    citation_sources: List[Dict[str, str]]
    stream_generator: Any

def retrieve_node(state: RagState) -> Dict:
    tracer = _get_tracer()
    vectorstore = get_vectorstore()
    original_question = state["question"]
    
    # ─── Query Rewriter ───
    if state.get("mode") == "fast":
        optimized_query = original_question
    else:
        with tracer.start_as_current_span("query_rewrite") as span:
            with timer("rewrite_latency", state["trace_data"]["metrics"]):
                rewrite_prompt = [
                    {"role": "system", "content": "You are a query rewriter for a Vector Database. Extract a standalone, highly searchable keyword query from the user's input. Return ONLY the optimized query string, nothing else."},
                    {"role": "user", "content": f"User query: {original_question}\n\nOptimized query:"}
                ]
                try:
                    optimized_query = generate_answer(rewrite_prompt, stream=False, model_key="gemini-flash-lite-latest")
                    optimized_query = optimized_query.strip('"').strip()
                    print(f"[PIPELINE] Query Rewritten: '{original_question}' -> '{optimized_query}'")
                except Exception as e:
                    print(f"[PIPELINE] Query rewriter failed: {e}. Using original.")
                    optimized_query = original_question

    with tracer.start_as_current_span("retrieval") as span:
        with timer("retrieval_latency", state["trace_data"]["metrics"]):
            initial_docs = retrieve(vectorstore, optimized_query, selected_files=state["selected_files"])
        print(f"[PIPELINE] Retrieved {len(initial_docs)} docs from Weaviate")
        for i, doc in enumerate(initial_docs):
            print(f"  [Doc {i+1}] source={doc.node.metadata.get('source','?')} text_len={len(doc.node.text)} score={doc.score}")
        span.set_attribute("retrieval.doc_count", len(initial_docs))
    return {"initial_docs": initial_docs}

def rerank_node(state: RagState) -> Dict:
    tracer = _get_tracer()
    with tracer.start_as_current_span("rerank") as span:
        with timer("rerank_latency", state["trace_data"]["metrics"]):
            initial_docs = state.get("initial_docs", [])
            TOP_K = 3
            ranked_docs = rerank(state["question"], initial_docs)[:TOP_K]
        print(f"[PIPELINE] Reranked to {len(ranked_docs)} docs")
        for i, doc in enumerate(ranked_docs):
            print(f"  [Ranked {i+1}] source={doc.node.metadata.get('source','?')} text_preview={doc.node.text[:80]!r}")
        span.set_attribute("rerank.doc_count", len(ranked_docs))
        
    contexts = [n.node.text for n in ranked_docs]
    source_docs = [n.node.metadata for n in ranked_docs]
    
    new_trace_data = state["trace_data"].copy()
    new_trace_data["contexts"] = contexts
    new_trace_data["source_docs"] = source_docs
    
    return {"ranked_docs": ranked_docs, "trace_data": new_trace_data}

def generate_node(state: RagState) -> Dict:
    tracer = _get_tracer()
    mode = state["mode"]
    
    # ─── Context Builder Formatting ───
    raw_contexts = state["trace_data"].get("contexts", [])
    raw_sources = state["trace_data"].get("source_docs", [])
    
    context_blocks = []
    import os
    for i, (text, meta) in enumerate(zip(raw_contexts, raw_sources)):
        raw_path = meta.get("source", "Unknown")
        filename = os.path.basename(raw_path) if raw_path != "Unknown" else "Unknown"
        context_blocks.append(f"[Dokumen {i+1}: {filename}]\n{text}")
        
    context_str = "\n\n".join(context_blocks)
    
    with tracer.start_as_current_span("generation") as span:
        if mode == "thinking":
            sys_instruct = (
                "Anda adalah asisten ahli. Jawablah dalam Bahasa Indonesia yang sangat profesional dan rapi.\n\n"
                "STRUKTUR JAWABAN WAJIB:\n"
                "1. Gunakan ## Judul Bagian (Bold Header) untuk memisahkan topik.\n"
                "2. Gunakan Penomoran Tebal (contoh: **1.**) untuk langkah-langkah atau poin utama.\n"
                "3. Gunakan Bullet Points untuk daftar detail.\n"
                "4. Berikan jarak 2 baris (double newline) antar paragraf agar tidak menumpuk.\n"
                "5. Gunakan **teks tebal** untuk istilah kunci.\n\n"
                "Berikan jawaban yang sangat detail berdasarkan konteks."
            )
        elif mode == "summarize":
            sys_instruct = (
                "Berikan rangkuman profesional dalam Bahasa Indonesia.\n"
                "Gunakan format Markdown: ## Judul, **1.** Poin Utama, dan Bullet Points. "
                "Pastikan ada jarak antar bagian."
            )
        else:  # fast
            sys_instruct = (
                "Jawablah dalam Bahasa Indonesia berdasarkan konteks.\n"
                "FORMAT WAJIB: Gunakan ## Header, **Poin Tebal**, dan daftar bullet. "
                "Pastikan tampilan sangat rapi dan mudah dibaca (gunakan banyak spasi/newline)."
            )

        new_trace_data = state["trace_data"].copy()
        new_trace_data["system_prompt"] = sys_instruct
        messages = build_prompt(context_str, state["question"], instruction=sys_instruct)
        span.set_attribute("llm.mode", mode)

        total_proc_latency = sum(new_trace_data["metrics"].values())
        new_trace_data["metrics"]["total_processing_latency"] = total_proc_latency

        # Gunakan actual_model_key dari state jika ada, override hanya untuk mode thinking
        actual_model_key = state.get("actual_model_key") or ("qwen3.6-27b" if mode == "thinking" else None)
        
        input_text = sys_instruct + "\n" + context_str + "\n" + state["question"]
        input_tokens = len(input_text) // 4
        
        # Pada mode stream, kita simpan messages & metadata saja — streaming dilakukan di luar node
        # agar tidak memblokir LangGraph's sync invoke()
        citation_sources = []
        import os
        for meta in new_trace_data.get("source_docs", []):
            raw_path = meta.get("source", "Unknown")
            filename = os.path.basename(raw_path) if raw_path != "Unknown" else "Unknown"
            citation_sources.append({"filename": filename, "full_path": raw_path})
        
        new_trace_data["citation"] = citation_sources
        new_trace_data["messages_for_stream"] = messages
        new_trace_data["actual_model_key_resolved"] = actual_model_key
        new_trace_data["input_tokens"] = input_tokens

        if not state.get("stream", False):
            with timer("llm_latency", new_trace_data["metrics"]):
                answer = generate_answer(messages, stream=False, model_key=actual_model_key)
            new_trace_data["answer"] = answer
            output_tokens = len(answer) // 4
            total_tokens = input_tokens + output_tokens
            new_trace_data["metrics"]["total_tokens"] = total_tokens
            new_trace_data["metrics"]["total_cost"] = (total_tokens / 1_000_000) * 0.05
            return {"trace_data": new_trace_data, "answer": answer}
        
        # Untuk mode stream, kembalikan trace_data yang sudah berisi messages_for_stream
        return {"trace_data": new_trace_data}

workflow = StateGraph(RagState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("rerank", rerank_node)
workflow.add_node("generate", generate_node)

workflow.add_edge("retrieve", "rerank")
workflow.add_edge("rerank", "generate")
workflow.add_edge("generate", END)
workflow.set_entry_point("retrieve")
rag_app = workflow.compile()

def run_rag(question: str, selected_files=None, mode="fast", stream=False, model_key=None) -> Dict[str, Any]:
    """
    Synchronous RAG pipeline. Untuk mode stream, kembalikan trace_data saja —
    streaming LLM dilakukan langsung di rag_event_generator menggunakan asyncio.to_thread.
    """
    trace_data = {
        "question": question,
        "answer": "",
        "contexts": [],
        "source_docs": [],
        "metrics": {},
        "system_prompt": "",
    }
    
    initial_state = {
        "question": question,
        "selected_files": selected_files,
        "mode": mode,
        "stream": stream,
        "actual_model_key": model_key,
        "trace_data": trace_data,
        "initial_docs": [],
        "ranked_docs": []
    }
    
    try:
        final_state = rag_app.invoke(initial_state)
        return final_state["trace_data"]
    except Exception as e:
        print(f"RAG Pipeline Error: {e}")
        raise e


async def run_rag_stream_events(question: str, selected_files=None, mode="fast", stream=False, model_key=None):
    """
    Async RAG pipeline that yields real-time progress steps while executing nodes.
    """
    trace_data = {
        "question": question,
        "answer": "",
        "contexts": [],
        "source_docs": [],
        "metrics": {},
        "system_prompt": "",
    }
    
    initial_state = {
        "question": question,
        "selected_files": selected_files,
        "mode": mode,
        "stream": stream,
        "actual_model_key": model_key,
        "trace_data": trace_data,
        "initial_docs": [],
        "ranked_docs": []
    }
    
    yield {"type": "thinking_step", "step": "retrieve", "content": "Retrieving relevant data from Knowledge Base..."}
    
    try:
        # astream will run the synchronous nodes in a background thread pool automatically
        async for output in rag_app.astream(initial_state):
            for node_name, state_update in output.items():
                if node_name == "retrieve":
                    yield {"type": "thinking_step", "step": "rerank", "content": "Reranking and selecting optimal documents..."}
                elif node_name == "rerank":
                    yield {"type": "thinking_step", "step": "generate", "content": "Synthesizing final response..."}
                elif node_name == "generate":
                    yield {"type": "done", "trace_data": state_update["trace_data"]}
    except Exception as e:
        print(f"RAG Pipeline Error: {e}")
        raise e

# ─── ASYNC MODE ROUTER ───────────────────────────────────────────────────────

async def run_rag_async(
    question: str,
    selected_files=None,
    mode: str = "reasoning",
    model_key: str = None
):
    """
    Async generator untuk mode reasoning dan deep_analytic.
    Yields event dicts: thinking_step, chunk, citation.
    """
    if mode == "reasoning":
        from src.application.rag.reasoning_agent import run_reasoning_rag
        async for event in run_reasoning_rag(question, selected_files=selected_files, model_key=model_key):
            yield event
    elif mode == "deep_analytic":
        from src.application.rag.graph_rag import run_graph_rag
        async for event in run_graph_rag(question, selected_files=selected_files, model_key=model_key):
            yield event
    else:
        raise ValueError(f"Mode '{mode}' tidak didukung oleh run_rag_async.")