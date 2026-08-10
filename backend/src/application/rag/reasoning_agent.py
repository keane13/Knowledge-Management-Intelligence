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


# ─── MAIN ASYNC GENERATOR ────────────────────────────────────────────────────

async def run_reasoning_rag(
    question: str,
    selected_files=None,
    stream: bool = True,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Pipeline Agentic Reasoning 5-tahap dengan streaming thinking steps.
    Yields event dicts yang kemudian diformat sebagai SSE di chat.py.
    """
    import asyncio

    vectorstore = get_vectorstore()
    all_sources: List[Dict] = []
    collected_answers: List[str] = []

    # ── STEP 1: PLANNING ────────────────────────────────────────────────────
    yield {
        "type": "thinking_step",
        "step": "planning",
        "content": f"🧠 **Memahami pertanyaan:** \"{question[:100]}{'...' if len(question) > 100 else ''}\"\n\nMenganalisis dan memecah menjadi sub-task..."
    }

    plan_messages = build_reasoning_prompt(question, phase="plan")
    try:
        plan_raw = _call_llm_sync(plan_messages, max_tokens=500)
        sub_tasks = _extract_json_array(plan_raw)
        if not sub_tasks:
            sub_tasks = [question]  # Fallback: satu task = pertanyaan itu sendiri
    except Exception as e:
        logger.warning(f"Planning failed: {e}, using single-task fallback")
        sub_tasks = [question]
        
    sub_tasks = sub_tasks[:3] # ENFORCE MAX_ITER = 3

    task_list_text = "\n".join([f"  {i+1}. {t}" for i, t in enumerate(sub_tasks)])
    yield {
        "type": "thinking_step",
        "step": "planning",
        "content": f"✅ **Rencana Riset:**\n{task_list_text}"
    }
    await asyncio.sleep(0.05)

    # ── STEP 2 & 3: TASK DECOMPOSE + EXECUTE ────────────────────────────────
    for idx, task in enumerate(sub_tasks):
        task_label = f"task_{idx + 1}"

        yield {
            "type": "thinking_step",
            "step": task_label,
            "content": f"🔍 **Mencari sumber untuk:** \"{task}\""
        }
        await asyncio.sleep(0.03)

        # Retrieve dokumen untuk sub-task ini
        try:
            raw_docs = retrieve(vectorstore, task, k=5, selected_files=selected_files)
            ranked = rerank(task, raw_docs)[:3]
            ctx_texts = [d.page_content for d, _ in ranked]
            ctx_metas = [d.metadata for d, _ in ranked]
            context_str = "\n\n".join(ctx_texts)

            # Kumpulkan sumber unik
            for meta in ctx_metas:
                src = meta.get("source", "Unknown")
                if src not in [s.get("source") for s in all_sources]:
                    all_sources.append({"source": src, "metadata": meta})

            yield {
                "type": "thinking_step",
                "step": task_label,
                "content": (
                    f"📄 **Ditemukan {len(ranked)} sumber relevan** untuk sub-task {idx+1}.\n"
                    f"Sumber: {', '.join(set(m.get('source', 'Unknown').split('/')[-1] for m in ctx_metas))}"
                )
            }
            await asyncio.sleep(0.03)

        except Exception as e:
            logger.warning(f"Retrieval error for task '{task}': {e}")
            context_str = ""
            yield {
                "type": "thinking_step",
                "step": task_label,
                "content": f"⚠️ Pencarian gagal untuk sub-task {idx+1}: {str(e)[:80]}"
            }

        # Execute: jawab sub-task dengan konteks
        if context_str:
            try:
                exec_messages = build_reasoning_prompt(
                    question, sub_task=task, context=context_str, phase="execute"
                )
                partial_answer = _call_llm_sync(exec_messages, max_tokens=800)
                collected_answers.append(f"[Sub-task {idx+1}: {task}]\n{partial_answer}")

                yield {
                    "type": "thinking_step",
                    "step": task_label,
                    "content": f"💡 **Insight sub-task {idx+1}:**\n{partial_answer[:300]}{'...' if len(partial_answer) > 300 else ''}"
                }
            except Exception as e:
                logger.warning(f"Execute error for task '{task}': {e}")
        else:
            collected_answers.append(f"[Sub-task {idx+1}: {task}]\nTidak ditemukan informasi relevan.")

        await asyncio.sleep(0.05)

    # ── STEP 4: REFLECT ──────────────────────────────────────────────────────
    yield {
        "type": "thinking_step",
        "step": "reflecting",
        "content": "🔄 **Mengevaluasi kelengkapan informasi yang terkumpul...**"
    }
    await asyncio.sleep(0.03)

    combined_partial = "\n\n".join(collected_answers)
    reflect_messages = build_reasoning_prompt(
        question, context=combined_partial, phase="reflect"
    )

    try:
        reflect_raw = _call_llm_sync(reflect_messages, max_tokens=300)
        reflect_result = _extract_json_reflect(reflect_raw)

        if not reflect_result.get("sufficient", True) and reflect_result.get("refined_query"):
            refined = reflect_result["refined_query"]
            missing = reflect_result.get("missing", "")

            yield {
                "type": "thinking_step",
                "step": "reflecting",
                "content": (
                    f"🔁 **Informasi kurang lengkap.** Yang kurang: {missing}\n"
                    f"Mencari tambahan dengan query: \"{refined}\"..."
                )
            }
            await asyncio.sleep(0.03)

            # Satu retrieval tambahan dengan refined query
            try:
                extra_docs = retrieve(vectorstore, refined, k=4, selected_files=selected_files)
                extra_ranked = rerank(refined, extra_docs)[:2]
                extra_ctx = "\n\n".join([d.page_content for d, _ in extra_ranked])
                for d, _ in extra_ranked:
                    src = d.metadata.get("source", "Unknown")
                    if src not in [s.get("source") for s in all_sources]:
                        all_sources.append({"source": src, "metadata": d.metadata})

                collected_answers.append(f"[Pencarian Tambahan: {refined}]\n{extra_ctx}")
                yield {
                    "type": "thinking_step",
                    "step": "reflecting",
                    "content": f"✅ **Informasi tambahan ditemukan.** Melanjutkan ke tahap sintesis..."
                }
            except Exception as e:
                logger.warning(f"Refined retrieval error: {e}")
        else:
            yield {
                "type": "thinking_step",
                "step": "reflecting",
                "content": "✅ **Informasi sudah cukup komprehensif.** Melanjutkan ke tahap sintesis jawaban akhir..."
            }
    except Exception as e:
        logger.warning(f"Reflection error: {e}")
        yield {
            "type": "thinking_step",
            "step": "reflecting",
            "content": "✅ Melanjutkan ke tahap sintesis..."
        }

    await asyncio.sleep(0.05)

    # ── STEP 5: GENERATE FINAL ANSWER ────────────────────────────────────────
    yield {
        "type": "thinking_step",
        "step": "generating",
        "content": "✍️ **Menyintesis jawaban akhir dari semua riset...**"
    }
    await asyncio.sleep(0.03)

    final_context = "\n\n".join(collected_answers)
    gen_messages = build_reasoning_prompt(
        question, context=final_context, phase="generate"
    )

    try:
        final_answer_raw = generate_reasoning_answer(
            gen_messages, stream=False, max_tokens=4000
        )
        if not isinstance(final_answer_raw, str):
            final_answer_raw = str(final_answer_raw)
    except Exception as e:
        final_answer_raw = f"Terjadi kesalahan saat generasi jawaban: {e}"

    # Stream final answer word-by-word
    for chunk in _stream_text_chunks(final_answer_raw):
        yield {"type": "chunk", "content": chunk}
        await asyncio.sleep(0.012)

    # ── CITATION ─────────────────────────────────────────────────────────────
    import os
    citation_sources = []
    seen = set()
    for src_info in all_sources:
        raw_path = src_info.get("source", "Unknown")
        filename = os.path.basename(raw_path) if raw_path != "Unknown" else "Unknown"
        if filename not in seen:
            seen.add(filename)
            citation_sources.append({
                "filename": filename,
                "full_path": raw_path,
            })

    yield {
        "type": "citation",
        "sources": citation_sources,
        "mode": "reasoning",
    }
