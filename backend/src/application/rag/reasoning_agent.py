"""
Reasoning Agent — Pipeline Agentic 5-Tahap
==========================================
Streaming events (SSE type: "thinking_step"):
  {"type": "thinking_step", "step": "planning",    "content": "..."}
  {"type": "thinking_step", "step": "task_N",      "content": "..."}
  {"type": "thinking_step", "step": "searching_N", "content": "..."}
  {"type": "thinking_step", "step": "reflecting",  "content": "..."}
  {"type": "thinking_step", "step": "generating",  "content": "..."}

Final answer:
  {"type": "chunk", "content": "..."}   (same as other modes, streamed word-by-word)

Citation:
  {"type": "citation", "sources": [...]}
"""

import json
import re
import logging
from typing import AsyncGenerator, Dict, Any, List

from src.application.rag.vectorstore import get_vectorstore
from src.application.rag.retriever import retrieve
from src.application.rag.reranker import rerank
from src.infrastructure.llm.llm import generate_reasoning_answer, REASONING_FALLBACK_CHAIN
from src.domain.prompt.prompt import build_reasoning_prompt

logger = logging.getLogger(__name__)


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _extract_json_array(text: str) -> list:
    """Ekstrak JSON array dari text LLM. Robust terhadap prefix/suffix teks."""
    text = text.strip()
    # Cari pattern [...] dalam text
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Fallback: split by newline jika tidak ada JSON
    lines = [l.strip().strip('"').strip("'").strip("-").strip()
             for l in text.split("\n") if l.strip()]
    return [l for l in lines if l][:3]  # MAX_ITER = 3 (strictly bound agent turns)


def _extract_json_reflect(text: str) -> dict:
    """Ekstrak JSON object dari reflection output."""
    text = text.strip()
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"sufficient": True, "missing": "", "refined_query": ""}


def _stream_text_chunks(text: str) -> list:
    """Pecah teks menjadi list chunk untuk simulasi streaming."""
    words = text.split(" ")
    return [w + (" " if i < len(words) - 1 else "") for i, w in enumerate(words)]


def _call_llm_sync(messages: list, max_tokens: int = 1500) -> str:
    """Panggil LLM secara synchronous, return string."""
    result = generate_reasoning_answer(messages, stream=False, max_tokens=max_tokens)
    if isinstance(result, str):
        return result
    # Jika somehow streaming object dikembalikan, consume-nya
    return str(result)



# ─── LANGGRAPH STATE & NODES ────────────────────────────────────────────────
from typing import TypedDict, Optional, List, Dict, Any, Union
from langgraph.graph import StateGraph, END
import asyncio

class AgentState(TypedDict):
    question: str
    selected_files: Optional[List[str]]
    stream: bool
    
    sub_tasks: List[str]
    current_task_idx: int
    
    all_sources: List[Dict]
    collected_answers: List[str]
    
    is_sufficient: bool
    refined_query: str
    missing: str
    
    # Store events to be yielded by the generator
    events: List[Dict[str, Any]]
    final_generator: Any
    final_sources: List[Dict[str, Any]]

async def plan_node(state: AgentState) -> Dict:
    question = state["question"]
    events = []
    
    events.append({
        "type": "thinking_step",
        "step": "planning",
        "content": f"🧠 **Memahami pertanyaan:** \"{question[:100]}{'...' if len(question) > 100 else ''}\"\n\nMenganalisis dan memecah menjadi sub-task..."
    })
    
    plan_messages = build_reasoning_prompt(question, phase="plan")
    try:
        plan_raw = _call_llm_sync(plan_messages, max_tokens=500)
        sub_tasks = _extract_json_array(plan_raw)
        if not sub_tasks:
            sub_tasks = [question]
    except Exception as e:
        logger.warning(f"Planning failed: {e}, using single-task fallback")
        sub_tasks = [question]
        
    sub_tasks = sub_tasks[:3] # ENFORCE MAX_ITER = 3
    
    task_list_text = "\n".join([f"  {i+1}. {t}" for i, t in enumerate(sub_tasks)])
    events.append({
        "type": "thinking_step",
        "step": "planning",
        "content": f"✅ **Rencana Riset:**\n{task_list_text}"
    })
    
    return {"sub_tasks": sub_tasks, "events": events, "current_task_idx": 0}

async def execute_task_node(state: AgentState) -> Dict:
    idx = state["current_task_idx"]
    task = state["sub_tasks"][idx]
    task_label = f"task_{idx + 1}"
    events = []
    
    events.append({
        "type": "thinking_step",
        "step": task_label,
        "content": f"🔍 **Mencari sumber untuk:** \"{task}\""
    })
    
    vectorstore = get_vectorstore()
    all_sources = state.get("all_sources", []).copy()
    collected_answers = state.get("collected_answers", []).copy()
    
    try:
        raw_docs = retrieve(vectorstore, task, k=5, selected_files=state.get("selected_files"))
        ranked = rerank(task, raw_docs)[:3]
        ctx_texts = [n.node.text for n in ranked]
        ctx_metas = [n.node.metadata for n in ranked]
        context_str = "\n\n".join(ctx_texts)
        
        for meta in ctx_metas:
            src = meta.get("source", "Unknown")
            if src not in [s.get("source") for s in all_sources]:
                all_sources.append({"source": src, "metadata": meta})
                
        events.append({
            "type": "thinking_step",
            "step": task_label,
            "content": (
                f"📄 **Ditemukan {len(ranked)} sumber relevan** untuk sub-task {idx+1}.\n"
                f"Sumber: {', '.join(set(m.get('source', 'Unknown').split('/')[-1] for m in ctx_metas))}"
            )
        })
    except Exception as e:
        logger.warning(f"Retrieval error for task '{task}': {e}")
        context_str = ""
        events.append({
            "type": "thinking_step",
            "step": task_label,
            "content": f"⚠️ Pencarian gagal untuk sub-task {idx+1}: {str(e)[:80]}"
        })
        
    if context_str:
        try:
            exec_messages = build_reasoning_prompt(
                state["question"], sub_task=task, context=context_str, phase="execute"
            )
            partial_answer = _call_llm_sync(exec_messages, max_tokens=800)
            collected_answers.append(f"[Sub-task {idx+1}: {task}]\n{partial_answer}")
            events.append({
                "type": "thinking_step",
                "step": task_label,
                "content": f"💡 **Insight sub-task {idx+1}:**\n{partial_answer[:300]}{'...' if len(partial_answer) > 300 else ''}"
            })
        except Exception as e:
            logger.warning(f"Execute error for task '{task}': {e}")
            collected_answers.append(f"[Sub-task {idx+1}: {task}]\nTidak ditemukan informasi relevan.")
    else:
        collected_answers.append(f"[Sub-task {idx+1}: {task}]\nTidak ditemukan informasi relevan.")
        
    return {
        "current_task_idx": idx + 1,
        "all_sources": all_sources,
        "collected_answers": collected_answers,
        "events": events
    }

async def reflect_node(state: AgentState) -> Dict:
    events = []
    events.append({
        "type": "thinking_step",
        "step": "reflecting",
        "content": "🔄 **Mengevaluasi kelengkapan informasi yang terkumpul...**"
    })
    
    combined_partial = "\n\n".join(state["collected_answers"])
    reflect_messages = build_reasoning_prompt(
        state["question"], context=combined_partial, phase="reflect"
    )
    
    try:
        reflect_raw = _call_llm_sync(reflect_messages, max_tokens=300)
        reflect_result = _extract_json_reflect(reflect_raw)
        
        is_sufficient = reflect_result.get("sufficient", True)
        refined_query = reflect_result.get("refined_query", "")
        missing = reflect_result.get("missing", "")
        
        if not is_sufficient and refined_query:
            events.append({
                "type": "thinking_step",
                "step": "reflecting",
                "content": (
                    f"🔁 **Informasi kurang lengkap.** Yang kurang: {missing}\n"
                    f"Mencari tambahan dengan query: \"{refined_query}\"..."
                )
            })
        
        return {
            "is_sufficient": is_sufficient,
            "refined_query": refined_query,
            "missing": missing,
            "events": events
        }
    except Exception as e:
        logger.warning(f"Reflection failed: {e}")
        return {"is_sufficient": True, "events": events}

async def extra_retrieve_node(state: AgentState) -> Dict:
    events = []
    vectorstore = get_vectorstore()
    all_sources = state.get("all_sources", []).copy()
    collected_answers = state.get("collected_answers", []).copy()
    refined = state["refined_query"]
    
    try:
        extra_docs = retrieve(vectorstore, refined, k=4, selected_files=state.get("selected_files"))
        extra_ranked = rerank(refined, extra_docs)[:2]
        extra_ctx = "\n\n".join([n.node.text for n in extra_ranked])
        for d in extra_ranked:
            src = d.node.metadata.get("source", "Unknown")
            if src not in [s.get("source") for s in all_sources]:
                all_sources.append({"source": src, "metadata": d.metadata})
        
        collected_answers.append(f"[Pencarian Tambahan: {refined}]\n{extra_ctx}")
        events.append({
            "type": "thinking_step",
            "step": "reflecting",
            "content": f"✅ **Informasi tambahan ditemukan.** Melanjutkan ke tahap sintesis..."
        })
    except Exception as e:
        events.append({
            "type": "thinking_step",
            "step": "reflecting",
            "content": f"⚠️ Pencarian tambahan gagal."
        })
        
    return {"all_sources": all_sources, "collected_answers": collected_answers, "events": events}

async def generate_final_node(state: AgentState) -> Dict:
    events = []
    events.append({
        "type": "thinking_step",
        "step": "generating",
        "content": "✨ **Menyusun jawaban akhir secara komprehensif...**"
    })
    
    combined_partial = "\n\n".join(state.get("collected_answers", []))
    final_messages = build_reasoning_prompt(
        state["question"], context=combined_partial, phase="generate"
    )
    
    final_sources = []
    import os
    for item in state.get("all_sources", []):
        raw_path = item.get("source", "Unknown")
        filename = os.path.basename(raw_path) if raw_path != "Unknown" else "Unknown"
        final_sources.append({"filename": filename, "full_path": raw_path})
        
    if state["stream"]:
        generator = generate_reasoning_answer(final_messages, stream=True, max_tokens=2500)
        return {"events": events, "final_generator": generator, "final_sources": final_sources}
    else:
        answer = _call_llm_sync(final_messages, max_tokens=2500)
        return {"events": events, "final_generator": answer, "final_sources": final_sources}


# ─── ROUTING LOGIC ─────────────────────────────────────────────────────────

def task_router(state: AgentState) -> str:
    if state["current_task_idx"] < len(state.get("sub_tasks", [])):
        return "execute_task"
    return "reflect"

def reflect_router(state: AgentState) -> str:
    if not state.get("is_sufficient", True) and state.get("refined_query"):
        return "extra_retrieve"
    return "generate_final"

# ─── BUILD GRAPH ───────────────────────────────────────────────────────────

builder = StateGraph(AgentState)
builder.add_node("plan", plan_node)
builder.add_node("execute_task", execute_task_node)
builder.add_node("reflect", reflect_node)
builder.add_node("extra_retrieve", extra_retrieve_node)
builder.add_node("generate_final", generate_final_node)

builder.set_entry_point("plan")
builder.add_conditional_edges("plan", lambda x: "execute_task")
builder.add_conditional_edges("execute_task", task_router)
builder.add_conditional_edges("reflect", reflect_router)
builder.add_edge("extra_retrieve", "generate_final")
builder.add_edge("generate_final", END)

reasoning_app = builder.compile()


# ─── MAIN ASYNC GENERATOR ────────────────────────────────────────────────────

async def run_reasoning_rag(
    question: str,
    selected_files=None,
    stream: bool = True,
    model_key: str = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Pipeline Agentic Reasoning 5-tahap dengan streaming thinking steps via LangGraph.
    Yields event dicts yang kemudian diformat sebagai SSE di chat.py.
    """
    import asyncio
    
    initial_state = {
        "question": question,
        "selected_files": selected_files,
        "stream": stream,
        "sub_tasks": [],
        "current_task_idx": 0,
        "all_sources": [],
        "collected_answers": [],
        "events": [],
    }
    
    # We use astream to step through the graph
    final_state = None
    async for output in reasoning_app.astream(initial_state):
        # Output is a dict mapping node_name -> state_updates
        for node_name, state_updates in output.items():
            if "events" in state_updates:
                for event in state_updates["events"]:
                    yield event
                    await asyncio.sleep(0.05)
            # update final_state reference
            final_state = state_updates

    if final_state and "final_generator" in final_state:
        gen = final_state["final_generator"]
        if stream:
            for chunk in gen:
                if chunk.choices[0].delta.content:
                    yield {
                        "type": "chunk",
                        "content": chunk.choices[0].delta.content
                    }
                await asyncio.sleep(0.01)
        else:
            yield {
                "type": "chunk",
                "content": gen
            }
            
        yield {
            "type": "citation",
            "sources": final_state.get("final_sources", [])
        }
