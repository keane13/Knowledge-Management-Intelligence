"""
GraphRAG Pipeline — Deep Analytic Mode
=======================================
Lightweight in-memory graph menggunakan NetworkX.
Tidak membutuhkan Neo4j atau database graph eksternal.

Flow:
  1. Retrieve top-10 chunks dari Weaviate
  2. Entity extraction (regex-based, tidak butuh LLM atau spaCy large model)
  3. Build in-memory NetworkX graph (node=entitas, edge=co-occurrence per chunk)
  4. BFS traversal dari entitas di question → enriched relationship context
  5. Generate dengan konteks gabungan (standard + graph paths)
  6. Streaming thinking_step events

Memory efficiency:
  - Graph hanya dari retrieved chunks (bukan seluruh KB)
  - Di-clear setelah response selesai
  - Pakai llama-3.3-70b-versatile (cepat, ringan)
"""

import re
import os
import json
import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


# ─── ENTITY EXTRACTION (REGEX-BASED, NO LLM) ─────────────────────────────────

# Pattern untuk entitas umum dalam dokumen bahasa Indonesia & Inggris
_ENTITY_PATTERNS = [
    # Angka + satuan (mis. "Rp 1.000.000", "50%", "2024")
    re.compile(r"\b(?:Rp\.?\s*)?\d[\d.,]*(?:\s*(?:%|persen|juta|miliar|ribu|USD|IDR|kg|ton))?\b"),
    # Nama proper (Title Case, 2+ kata)
    re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"),
    # Akronim / singkatan (ALL CAPS 2-6 karakter)
    re.compile(r"\b[A-Z]{2,6}\b"),
    # Nama produk/brand dengan angka (mis. "Python 3.12", "GPT-4", "Laravel 10")
    re.compile(r"\b[A-Z][a-zA-Z]*[-\s]?\d+(?:\.\d+)?\b"),
    # Tahun (1900-2099)
    re.compile(r"\b(?:19|20)\d{2}\b"),
    # Kata kunci domain (kata benda teknis umum)
    re.compile(r"\b(?:sistem|proses|metode|model|algoritma|platform|layanan|fitur|modul|database|server|API|machine learning|deep learning|neural network)\b", re.IGNORECASE),
]

_STOPWORDS = {
    "dan", "atau", "yang", "di", "ke", "dari", "pada", "untuk", "dengan", "adalah",
    "ini", "itu", "the", "a", "an", "and", "or", "in", "of", "to", "is", "are",
    "was", "were", "be", "been", "by", "as", "at", "for", "on", "with",
}


def extract_entities(text: str) -> List[str]:
    """Ekstrak entitas dari teks menggunakan regex. Cepat, hemat memori."""
    entities: Set[str] = set()
    for pattern in _ENTITY_PATTERNS:
        for match in pattern.finditer(text):
            entity = match.group().strip()
            if len(entity) >= 2 and entity.lower() not in _STOPWORDS:
                entities.add(entity)
    return list(entities)


def extract_entities_from_question(question: str) -> List[str]:
    """Ekstrak entitas spesifik dari pertanyaan user untuk BFS seeding."""
    entities = extract_entities(question)
    # Tambahkan kata-kata panjang (>4 karakter) bukan stopword sebagai potential entity
    for word in question.split():
        clean = re.sub(r"[^\w]", "", word)
        if len(clean) > 4 and clean.lower() not in _STOPWORDS:
            entities.append(clean)
    return list(set(entities))


# ─── GRAPH BUILDER ────────────────────────────────────────────────────────────

def build_entity_graph(chunks: List[Tuple[str, dict]]):
    """
    Bangun NetworkX graph dari chunks.
    Node: entitas
    Edge: co-occurrence dalam chunk yang sama (weighted)
    
    Returns (graph, chunk_entity_map)
    """
    try:
        import networkx as nx
    except ImportError:
        logger.warning("networkx not installed. Graph features disabled.")
        return None, {}

    G = nx.Graph()
    chunk_entity_map: Dict[int, List[str]] = {}  # chunk_idx → [entities]

    for idx, (text, meta) in enumerate(chunks):
        entities = extract_entities(text)
        chunk_entity_map[idx] = entities

        # Add nodes dengan metadata
        for ent in entities:
            if not G.has_node(ent):
                G.add_node(ent, chunks=[idx], sources=[meta.get("source", "Unknown")])
            else:
                G.nodes[ent]["chunks"].append(idx)
                G.nodes[ent]["sources"].append(meta.get("source", "Unknown"))

        # Add edges (co-occurrence)
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                e1, e2 = entities[i], entities[j]
                if G.has_edge(e1, e2):
                    G[e1][e2]["weight"] += 1
                    G[e1][e2]["chunks"].append(idx)
                else:
                    G.add_edge(e1, e2, weight=1, chunks=[idx])

    return G, chunk_entity_map


def bfs_traverse(G, seed_entities: List[str], max_depth: int = 2, max_nodes: int = 20) -> List[tuple]:
    """
    BFS dari seed entitas, return list of (entity, neighbor, weight, depth).
    Memory-efficient: bounded depth dan max_nodes.
    """
    if G is None:
        return []

    try:
        import networkx as nx
    except ImportError:
        return []

    visited = set()
    paths = []
    queue = [(ent, 0) for ent in seed_entities if G.has_node(ent)]

    while queue and len(visited) < max_nodes:
        node, depth = queue.pop(0)
        if node in visited or depth > max_depth:
            continue
        visited.add(node)

        if depth < max_depth:
            neighbors = sorted(
                G.neighbors(node),
                key=lambda n: G[node][n].get("weight", 0),
                reverse=True
            )[:5]  # Top-5 neighbors per node
            for neighbor in neighbors:
                if neighbor not in visited:
                    edge_data = G[node].get(neighbor, G[node][neighbor] if G.has_edge(node, neighbor) else {})
                    weight = G[node][neighbor].get("weight", 1) if G.has_edge(node, neighbor) else 0
                    paths.append((node, neighbor, weight, depth))
                    queue.append((neighbor, depth + 1))

    return paths


def paths_to_context_text(paths: List[tuple], chunks: List[Tuple[str, dict]], G) -> str:
    """Konversi graph paths menjadi teks konteks yang readable."""
    if not paths:
        return "Tidak ada relasi graph yang ditemukan."

    lines = ["**Relasi Entitas Ditemukan:**\n"]
    seen_pairs = set()

    for (src, dst, weight, depth) in paths[:15]:  # Max 15 paths
        pair = tuple(sorted([src, dst]))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        # Cari chunk yang mengandung kedua entitas
        if G and G.has_edge(src, dst):
            shared_chunks = G[src][dst].get("chunks", [])
            chunk_snippets = []
            for ci in shared_chunks[:1]:  # Max 1 chunk per edge
                if ci < len(chunks):
                    snippet = chunks[ci][0][:200].replace("\n", " ")
                    chunk_snippets.append(f'  → "{snippet}..."')

            line = f"- **{src}** ↔ **{dst}** (co-occurrence: {weight}x)"
            if chunk_snippets:
                line += "\n" + "\n".join(chunk_snippets)
            lines.append(line)

    return "\n".join(lines)



# ─── LANGGRAPH STATE & NODES ────────────────────────────────────────────────
from typing import TypedDict, Optional, List, Dict, Any, Union, Tuple
from langgraph.graph import StateGraph, END
import asyncio
import os

class GraphRagState(TypedDict):
    question: str
    selected_files: Optional[List[str]]
    stream: bool
    
    ranked_docs: List[Any]
    chunks: List[Tuple[str, dict]]
    all_sources: List[Dict]
    
    G: Any
    chunk_entity_map: dict
    
    graph_context: str
    standard_context: str
    
    events: List[Dict[str, Any]]
    final_answer: str
    final_sources: List[Dict[str, Any]]

async def retrieve_node(state: GraphRagState) -> Dict:
    from src.application.rag.vectorstore import get_vectorstore
    from src.application.rag.retriever import retrieve
    from src.application.rag.reranker import rerank
    
    events = []
    question = state["question"]
    
    events.append({
        "type": "thinking_step",
        "step": "searching",
        "content": f"🔍 **Deep Analytic:** Mencari dokumen relevan untuk analisis mendalam...\nQuery: \"{question[:100]}\""
    })
    
    vectorstore = get_vectorstore()
    all_sources = []
    
    try:
        raw_docs = retrieve(vectorstore, question, k=10, selected_files=state.get("selected_files"))
        ranked_docs = rerank(question, raw_docs)[:8]
    except Exception as e:
        logger.error(f"GraphRAG retrieval error: {e}")
        events.append({
            "type": "thinking_step",
            "step": "searching",
            "content": f"❌ Gagal mengambil dokumen: {str(e)[:100]}"
        })
        return {"events": events, "final_answer": f"Terjadi kesalahan saat mengambil dokumen: {e}"}
        
    chunks = [(n.node.text, n.node.metadata) for n in ranked_docs]
    standard_context = "\n\n".join([c[0] for c in chunks[:5]])
    
    for d in ranked_docs:
        src = d.node.metadata.get("source", "Unknown")
        if src not in [s.get("source") for s in all_sources]:
            all_sources.append({"source": src, "metadata": d.metadata})
            
    events.append({
        "type": "thinking_step",
        "step": "searching",
        "content": (
            f"✅ **{len(ranked_docs)} dokumen ditemukan.**\n"
            f"Sumber: {', '.join(set(os.path.basename(c[1].get('source', 'Unknown')) for c in chunks[:5]))}"
        )
    })
    
    return {
        "ranked_docs": ranked_docs,
        "chunks": chunks,
        "standard_context": standard_context,
        "all_sources": all_sources,
        "events": events
    }

async def build_graph_node(state: GraphRagState) -> Dict:
    events = []
    if "final_answer" in state and state["final_answer"]:
        return {} # Short-circuit if failed in retrieve
        
    events.append({
        "type": "thinking_step",
        "step": "graph_building",
        "content": "🕸️ **Membangun knowledge graph** dari entitas dalam dokumen..."
    })
    
    G, chunk_entity_map = build_entity_graph(state.get("chunks", []))
    
    if G is not None:
        node_count = G.number_of_nodes()
        edge_count = G.number_of_edges()
        events.append({
            "type": "thinking_step",
            "step": "graph_building",
            "content": (
                f"✅ **Graph dibangun:** {node_count} entitas, {edge_count} relasi.\n"
                f"Mencari jalur relasi yang relevan dengan pertanyaan..."
            )
        })
    else:
        events.append({
            "type": "thinking_step",
            "step": "graph_building",
            "content": "⚠️ Graph module tidak tersedia, menggunakan standard RAG context."
        })
        
    return {"G": G, "chunk_entity_map": chunk_entity_map, "events": events}

async def traverse_node(state: GraphRagState) -> Dict:
    events = []
    if "final_answer" in state and state["final_answer"]:
        return {}
        
    graph_context = ""
    G = state.get("G")
    chunks = state.get("chunks", [])
    question = state["question"]
    
    if G is not None and G.number_of_nodes() > 0:
        events.append({
            "type": "thinking_step",
            "step": "graph_traversal",
            "content": "🔗 **Menelusuri relasi antar entitas** (BFS traversal)..."
        })
        
        seed_entities = extract_entities_from_question(question)
        paths = bfs_traverse(G, seed_entities, max_depth=2, max_nodes=25)
        
        if paths:
            graph_context = paths_to_context_text(paths, chunks, G)
            events.append({
                "type": "thinking_step",
                "step": "graph_traversal",
                "content": (
                    f"✅ **{len(paths)} jalur relasi ditemukan.**\n"
                    f"Seed entitas: {', '.join(seed_entities[:5])}"
                )
            })
        else:
            graph_context = "Tidak ditemukan relasi graph yang spesifik untuk pertanyaan ini."
            events.append({
                "type": "thinking_step",
                "step": "graph_traversal",
                "content": "ℹ️ Tidak ditemukan jalur relasi spesifik. Menggunakan standard context."
            })
            
    return {"graph_context": graph_context, "events": events}

async def generate_node(state: GraphRagState) -> Dict:
    from src.infrastructure.llm.llm import generate_answer, GRAPH_ANALYTIC_MODEL
    from src.domain.prompt.prompt import build_graph_analytic_prompt
    
    events = []
    if "final_answer" in state and state["final_answer"]:
        return {}
        
    events.append({
        "type": "thinking_step",
        "step": "generating",
        "content": "✍️ **Menganalisis dan menyintesis jawaban** dari dokumen + knowledge graph..."
    })
    
    messages = build_graph_analytic_prompt(
        state["question"], 
        state.get("standard_context", ""), 
        state.get("graph_context", "")
    )
    
    try:
        answer_raw = generate_answer(messages, stream=False, model_key=GRAPH_ANALYTIC_MODEL)
        if not isinstance(answer_raw, str):
            answer_raw = str(answer_raw)
    except Exception as e:
        logger.error(f"GraphRAG generation error: {e}")
        answer_raw = f"Terjadi kesalahan saat analisis: {e}"
        
    citation_sources = []
    seen = set()
    for src_info in state.get("all_sources", []):
        raw_path = src_info.get("source", "Unknown")
        filename = os.path.basename(raw_path) if raw_path != "Unknown" else "Unknown"
        if filename not in seen:
            seen.add(filename)
            citation_sources.append({
                "filename": filename,
                "full_path": raw_path,
            })
            
    return {"events": events, "final_answer": answer_raw, "final_sources": citation_sources}


async def evaluate_node(state: GraphRagState) -> Dict:
    from src.infrastructure.llm.llm import generate_answer, GRAPH_ANALYTIC_MODEL
    events = []
    if "final_answer" not in state or not state["final_answer"]:
        return {}
        
    events.append({
        "type": "thinking_step",
        "step": "evaluating",
        "content": "⚖️ **LLM-as-a-Judge:** Mengevaluasi dan memoles kualitas jawaban akhir..."
    })
    
    judge_prompt = (
        "Anda adalah AI Hakim (LLM-as-a-Judge) yang bertugas mengevaluasi jawaban dari asisten AI lain.\n"
        "Tugas Anda:\n"
        "1. Periksa apakah jawaban tersebut akurat berdasarkan konteks yang diberikan.\n"
        "2. Perbaiki, perjelas, atau tambahkan detail penting jika ada yang terlewat.\n"
        "3. Jika jawaban sudah bagus, poles bahasanya agar lebih profesional dan rapi.\n"
        "4. KEMBALIKAN HANYA JAWABAN YANG SUDAH DIPERBAIKI. Jangan sertakan pengantar seperti 'Berikut adalah perbaikannya'."
    )
    
    user_content = (
        f"Pertanyaan Asli: {state['question']}\n\n"
        f"Konteks Dokumen & Graph: {state.get('standard_context', '')}\n{state.get('graph_context', '')}\n\n"
        f"Jawaban Awal AI: {state['final_answer']}\n\n"
        "Silakan evaluasi dan berikan jawaban versi final yang terbaik."
    )
    
    messages = [
        {"role": "system", "content": judge_prompt},
        {"role": "user", "content": user_content}
    ]
    
    try:
        judged_answer = generate_answer(messages, stream=False, model_key=GRAPH_ANALYTIC_MODEL)
        if not isinstance(judged_answer, str):
            judged_answer = str(judged_answer)
    except Exception as e:
        logger.error(f"GraphRAG evaluate error: {e}")
        judged_answer = state["final_answer"]
        
    events.append({
        "type": "thinking_step",
        "step": "evaluating",
        "content": "✅ **Evaluasi Selesai:** Jawaban telah divalidasi dan dioptimalkan."
    })
        
    return {"events": events, "final_answer": judged_answer}

builder = StateGraph(GraphRagState)
builder.add_node("retrieve", retrieve_node)
builder.add_node("build_graph", build_graph_node)
builder.add_node("traverse", traverse_node)
builder.add_node("generate", generate_node)
builder.add_node("evaluate", evaluate_node)

builder.set_entry_point("retrieve")
builder.add_edge("retrieve", "build_graph")
builder.add_edge("build_graph", "traverse")
builder.add_edge("traverse", "generate")
builder.add_edge("generate", "evaluate")
builder.add_edge("evaluate", END)

graph_app = builder.compile()

# ─── MAIN ASYNC GENERATOR ────────────────────────────────────────────────────

async def run_graph_rag(
    question: str,
    selected_files=None,
    stream: bool = True,
    model_key: str = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Deep Analytic: GraphRAG pipeline dengan streaming thinking steps via LangGraph.
    """
    import asyncio
    
    initial_state = {
        "question": question,
        "selected_files": selected_files,
        "stream": stream,
        "events": [],
    }
    
    final_state = None
    async for output in graph_app.astream(initial_state):
        for node_name, state_updates in output.items():
            if "events" in state_updates:
                for event in state_updates["events"]:
                    yield event
                    await asyncio.sleep(0.05)
            final_state = state_updates
            
    if final_state and "final_answer" in final_state:
        answer_raw = final_state["final_answer"]
        words = answer_raw.split(" ")
        for i, w in enumerate(words):
            yield {"type": "chunk", "content": w + (" " if i < len(words) - 1 else "")}
            await asyncio.sleep(0.012)
            
        yield {
            "type": "citation",
            "sources": final_state.get("final_sources", []),
            "mode": "deep_analytic",
        }
