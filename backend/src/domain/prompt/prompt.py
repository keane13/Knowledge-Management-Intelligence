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


def build_reasoning_prompt(question: str, sub_task: str = "", context: str = "", phase: str = "plan") -> list:
    """
    Prompt untuk setiap fase di Reasoning Agent:
    - phase='plan'    : memecah pertanyaan menjadi sub-task
    - phase='execute' : menjawab satu sub-task dengan konteks
    - phase='reflect' : evaluasi apakah konteks sudah cukup
    - phase='generate': sintesis jawaban akhir
    """
    if phase == "plan":
        system = (
            "Anda adalah Reasoning AI yang sistematis dan analitis.\n"
            "Tugas Anda: pecah pertanyaan kompleks menjadi 2-4 sub-task yang konkret dan spesifik.\n"
            "Format output WAJIB (JSON array):\n"
            '["sub_task_1", "sub_task_2", "sub_task_3"]\n'
            "HANYA output JSON array. Tidak ada teks lain."
        )
        user_content = f"Pertanyaan utama: {question}"

    elif phase == "execute":
        system = (
            "Anda adalah asisten peneliti profesional. Jawab dalam Bahasa Indonesia.\n"
            "Jawab HANYA berdasarkan konteks dokumen yang diberikan.\n"
            "Jika informasi tidak tersedia di konteks, katakan 'Tidak ditemukan dalam dokumen.'"
        )
        user_content = (
            f"Sub-task: {sub_task}\n\n"
            f"Konteks Dokumen:\n{context}\n\n"
            "Jawab sub-task ini secara ringkas dan faktual."
        )

    elif phase == "reflect":
        system = (
            "Anda adalah Evaluator yang kritis. Evaluasi apakah jawaban yang dikumpulkan sudah cukup menjawab pertanyaan.\n"
            "Output WAJIB format JSON: {\"sufficient\": true/false, \"missing\": \"apa yang kurang\", \"refined_query\": \"query pencarian lebih baik jika perlu\"}\n"
            "HANYA output JSON."
        )
        user_content = (
            f"Pertanyaan Asli: {question}\n\n"
            f"Jawaban yang Dikumpulkan:\n{context}\n\n"
            "Apakah jawaban sudah cukup komprehensif?"
        )

    else:  # phase == 'generate'
        system = (
            "Anda adalah asisten ahli yang profesional. Jawab dalam Bahasa Indonesia yang sangat baik dan terstruktur.\n\n"
            "TUGAS UTAMA:\n"
            "Hasilkan jawaban akhir yang SANGAT PANJANG, MENDETAIL, dan KOMPREHENSIF. "
            "Jangan ragu untuk menguraikan setiap aspek dari konteks secara panjang lebar.\n\n"
            "STRUKTUR JAWABAN WAJIB:\n"
            "1. Gunakan ## Judul Bagian untuk memisahkan topik.\n"
            "2. Gunakan **teks tebal** untuk poin kunci dan istilah penting.\n"
            "3. Gunakan bullet points untuk mendaftar setiap detail kecil yang relevan.\n"
            "4. Berikan spasi 2 baris antar paragraf.\n"
            "5. Akhiri dengan bagian **Kesimpulan** yang merangkum keseluruhan poin.\n\n"
            "Sintesis SEMUA informasi dari riset Anda menjadi jawaban akhir yang sangat panjang dan memuaskan."
        )
        user_content = (
            f"Pertanyaan Asli: {question}\n\n"
            f"Hasil Riset (dari beberapa sumber):\n{context}\n\n"
            "Buat jawaban akhir yang sangat komprehensif, panjang, terstruktur, dan profesional. Jangan berikan jawaban singkat."
        )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]


def build_graph_analytic_prompt(question: str, standard_context: str, graph_context: str) -> list:
    """
    Prompt untuk mode Deep Analytic (GraphRAG).
    Menekankan analisis relasi antar entitas.
    """
    system = (
        "Anda adalah analis data dan knowledge graph yang setara dengan ilmuwan data tingkat lanjut. Jawab dalam Bahasa Indonesia.\n\n"
        "Anda mendapatkan DUA sumber informasi:\n"
        "1. KONTEKS DOKUMEN: Teks langsung dari dokumen.\n"
        "2. KONTEKS GRAPH: Jalur relasi antar entitas yang ditemukan dalam dokumen.\n\n"
        "TUGAS UTAMA:\n"
        "Buatlah laporan analisis yang EKSTREMELY PANJANG, SANGAT MENDETAIL, dan AKADEMIS. "
        "Kupas tuntas setiap entitas dan hubungan (edge) yang ada dalam graph.\n\n"
        "STRUKTUR ANALISIS WAJIB:\n"
        "  ## 1. Pemetaan Entitas Kunci\n"
        "  Jelaskan secara panjang lebar setiap entitas yang ditemukan beserta perannya.\n\n"
        "  ## 2. Analisis Relasi Mendalam (Graph)\n"
        "  Uraikan setiap hubungan antar entitas. Jika ada co-occurrence, jelaskan apa makna dari co-occurrence tersebut "
        "berdasarkan konteks dokumen secara ekstensif.\n\n"
        "  ## 3. Implikasi & Temuan Kritis\n"
        "  Berikan wawasan mendalam atau temuan tersembunyi (hidden insights).\n\n"
        "  ## 4. Kesimpulan Akhir\n"
        "  Rangkuman laporan secara utuh.\n\n"
        "DILARANG MEMBERIKAN JAWABAN PENDEK. Uraikan setiap poin secara maksimal."
    )
    user_content = (
        f"Pertanyaan: {question}\n\n"
        f"--- KONTEKS DOKUMEN ---\n{standard_context}\n\n"
        f"--- KONTEKS GRAPH (Relasi Entitas) ---\n{graph_context}\n\n"
        "Buat laporan analisis yang sangat panjang dan mendalam berdasarkan kedua sumber di atas, "
        "mengikuti struktur 4 bagian yang diwajibkan."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]