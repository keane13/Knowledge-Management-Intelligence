from rag.loader import load_documents
from rag.splitter import split_docs
from rag.vectorestore import get_vectorstore
from rag.retriever import retrieve
from rag.reranker import rerank
from llm.llm import generate_answer
from llm.prompt import build_prompt
from config.configs import DOCS_PATH

def run_rag(question, selected_files=None, mode="fast", stream=False):
    docs = load_documents(DOCS_PATH)
    chunks = split_docs(docs)
    vectorstore = get_vectorstore(chunks)

    retrieved = retrieve(vectorstore, question, selected_files=selected_files)
    ranked = rerank(question, retrieved)[:5]

    context = "\n\n".join(d.page_content for d, _ in ranked)
    
    # Mode logic
    final_question = question
    if mode == "thinking":
        final_question = f"Let's think step by step to answer this question detailedly:\n{question}"
    elif mode == "summarize":
        final_question = f"Please provide a concise summary of the answer to this question based on the context:\n{question}"
    
    messages = build_prompt(context, final_question)
    answer = generate_answer(messages, stream=stream)
    
    return answer, context
