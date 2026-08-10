# Default Persona (Gaya Teknokratis)
DEFAULT_SYSTEM_PROMPT = """
You are a professional knowledge assistant. Answer with teknokratis style. In Bahasa Indonesia yang baik dan Benar.
Answer ONLY using the provided context.
If the answer is not in the context, say:
"I don't have enough information in the document."
If the answer contains toxic and harmful content, say:
"I cannot answer this question."
"""

def build_prompt(context, question, instruction=None):
    """
    Membangun prompt.
    - context: Teks dokumen.
    - question: Pertanyaan user.
    - instruction: Instruksi tambahan dari run_rag (misal: "Think step by step").
    """
    
    # 1. Mulai dengan prompt dasar teknokratis
    final_system_content = DEFAULT_SYSTEM_PROMPT
    
    # 2. Jika ada instruksi mode (Thinking/Summarize), tambahkan ke sistem prompt
    #    Ini penting agar gaya 'Teknokratis' tidak hilang saat mode berubah.
    if instruction:
        final_system_content += f"\n\nAdditional Instruction:\n{instruction}"

    return [
        {"role": "system", "content": final_system_content},
        {
            "role": "user",
            "content": f"""
Context:
{context}

Question:
{question}

Answer based on the context, with profesional clear long final answer.
"""
        }
    ]