import re
import datetime
from pathlib import Path
from llama_index.core import Document as LlamaDocument
import pymupdf  # PyMuPDF

# Docling Imports
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

# -------------------------
# 1. GLOBAL CONVERTER (SPEED FIX)
# -------------------------
_DOCLING_CONVERTER = None

def get_docling_converter(enable_ocr: bool = True):
    """Singleton pattern agar model Docling diload hanya 1 kali di memori."""
    global _DOCLING_CONVERTER
    if _DOCLING_CONVERTER is None:
        print("⚙️ Inisialisasi Model Docling (Hanya 1 kali, mohon tunggu)...")
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = enable_ocr  
        pipeline_options.do_table_structure = True 
        pipeline_options.table_structure_options.do_cell_matching = True

        _DOCLING_CONVERTER = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _DOCLING_CONVERTER

# -------------------------
# 2. EXTRACTORS & UTILITIES
# -------------------------
def is_gibberish(text: str) -> bool:
    """
    Mendeteksi apakah teks rusak (corrupt font / bad OCR / Mojibake).
    Ciri-cirinya: terlalu banyak karakter aneh atau kurangnya huruf standar.
    """
    if not text or len(text) < 50:
        return True
        
    # Hitung jumlah huruf dan angka standar
    alphanumeric_count = len(re.findall(r'[a-zA-Z0-9]', text))
    alphanumeric_ratio = alphanumeric_count / len(text)
    
    # Hitung jumlah simbol aneh (selain spasi, huruf, angka, dan tanda baca umum)
    weird_symbols_count = len(re.findall(r'[^a-zA-Z0-9\s\.,\-\?!\(\)]', text))
    weird_symbols_ratio = weird_symbols_count / len(text)
    
    # Kriteria Gibberish:
    # 1. Jika kurang dari 65% teks adalah huruf/angka, ATAU
    # 2. Jika lebih dari 5% teks adalah simbol aneh
    if alphanumeric_ratio < 0.65 or weird_symbols_ratio > 0.05:
        return True
        
    return False

def extract_with_pymupdf(pdf_path: str) -> str:
    """Ekstraksi super cepat untuk PDF berbasis teks (digital born)."""
    try:
        doc = pymupdf.open(pdf_path)
        texts = []
        for page in doc:
            text = page.get_text("text")
            if text:
                texts.append(text)
        return "\n".join(texts).strip()
    except Exception as e:
        print(f"⚠️ PyMuPDF Error on {pdf_path}: {e}")
        return ""

def extract_with_liteparse(pdf_path: str) -> str:
    """Ekstraksi menggunakan liteParse."""
    try:
        from liteparse import LiteParse
        parser = LiteParse(
            output_format="markdown",
            image_mode="placeholder",
            extract_links=True,
        )
        result = parser.parse(pdf_path)
        return result.text.strip() if result and hasattr(result, 'text') else ""
    except ImportError:
        print("⚠️ liteparse belum diinstall (pip install liteparse).")
        return ""
    except Exception as e:
        print(f"⚠️ liteParse Error on {pdf_path}: {e}")
        return ""

def extract_with_docling(pdf_path: str) -> str:
    """Ekstraksi cerdas. Menggunakan Global Converter."""
    try:
        converter = get_docling_converter()
        result = converter.convert(pdf_path)
        
        if not result or not result.document:
            return ""

        return result.document.export_to_markdown().strip()
    except Exception as e:
        print(f"❌ Docling Error on {pdf_path}: {e}")
        return ""

def extract_word(docx_path: str) -> str:
    """Ekstraksi teks dari file Word (.docx) menggunakan python-docx."""
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(docx_path)
        parts = []

        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text.strip())

        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)

        return "\n".join(parts).strip()
    except ImportError:
        print("❌ python-docx not installed. Run: pip install python-docx")
        return ""
    except Exception as e:
        print(f"❌ Word extraction error on {docx_path}: {e}")
        return ""

def extract_image(image_path: str) -> str:
    """Ekstraksi teks dari file gambar menggunakan pytesseract OCR/OpenRouter Vision."""
    # 1. Coba pytesseract dulu (cepat dan lokal)
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="eng+ind").strip()
        if text and len(text) > 10:
            print(f"   ✅ OCR via pytesseract ({len(text)} chars)")
            return text
        print("   ⚠️ pytesseract returned empty/short text — trying OpenRouter Vision...")
    except Exception as e:
        print(f"   ⚠️ pytesseract error: {e} — trying OpenRouter Vision...")

    # 2. Fallback ke OpenRouter Vision LLM
    try:
        import base64
        import requests
        from pathlib import Path
        from src.infrastructure.config.configs import OPENROUTER_API_KEY
        
        # Encode image to base64
        path = Path(image_path)
        suffix = path.suffix.lower().lstrip(".")
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "bmp": "bmp"}
        mime = mime_map.get(suffix, "jpeg")
        
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        data_url = f"data:image/{mime};base64,{b64}"
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gemini-3.1-flash-lite", # Fast and free vision model
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all readable text from this image exactly as it appears. If there is no text, return 'NO_TEXT_FOUND'. Do not add any conversational filler or explanations."},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 2000
        }
        
        print(f"   ⏳ Calling OpenRouter Vision for {path.name}...")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            extracted = data['choices'][0]['message']['content'].strip()
            if extracted and "NO_TEXT_FOUND" not in extracted:
                print(f"   ✅ OCR via OpenRouter Vision ({len(extracted)} chars)")
                return extracted
            else:
                print("   ⚠️ OpenRouter Vision found no text.")
                return ""
        else:
            print(f"   ❌ OpenRouter Vision API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ OpenRouter Vision error: {e}")

    return ""

    return ""

def extract_audio(audio_path: str) -> str:
    """Ekstraksi teks dari file audio menggunakan Whisper Groq."""
    try:
        from groq import Groq
        from src.infrastructure.config.configs import GROQ_API_KEY
        client = Groq(api_key=GROQ_API_KEY)
        
        print(f"   ⏳ Calling Groq Whisper for {Path(audio_path).name}...")
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(Path(audio_path).name, file.read()),
              model="whisper-large-v3",
              response_format="text"
            )
        
        text = str(transcription).strip()
        if text:
            print(f"   ✅ Audio transcribed ({len(text)} chars)")
            return text
    except Exception as e:
        print(f"   ❌ Audio transcription error: {e}")
    return ""

def extract_ppt(ppt_path: str) -> str:
    """Ekstraksi teks dari presentasi PowerPoint."""
    try:
        from pptx import Presentation
        prs = Presentation(ppt_path)
        parts = []
        for slide_idx, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text.strip())
            if slide_text:
                parts.append(f"--- Slide {slide_idx + 1} ---\n" + "\n".join(slide_text))
        return "\n\n".join(parts).strip()
    except Exception as e:
        print(f"   ❌ PPT extraction error: {e}")
    return ""

def extract_excel(excel_path: str) -> str:
    """Ekstraksi teks dari file Excel menjadi Markdown tables."""
    try:
        import pandas as pd
        # Membaca semua sheet
        xls = pd.read_excel(excel_path, sheet_name=None)
        parts = []
        for sheet_name, df in xls.items():
            # Ubah df menjadi markdown
            md_table = df.to_markdown(index=False)
            if md_table:
                parts.append(f"### Sheet: {sheet_name}\n\n{md_table}")
        return "\n\n".join(parts).strip()
    except Exception as e:
        print(f"   ❌ Excel extraction error: {e}")
    return ""

# -------------------------
# SUPPORTED EXTENSIONS
# -------------------------
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
WORD_EXTENSIONS  = {".docx", ".doc"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
PPT_EXTENSIONS   = {".pptx", ".ppt"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# -------------------------
# 3. MAIN LOADER — load a single file
# -------------------------
def load_single_document(file_path: str, min_text_length: int = 300):
    """
    Load and extract text from a single file.
    Returns a LlamaIndex Document.
    """
    file = Path(file_path)
    suffix = file.suffix.lower()

    # -------- PDF --------
    if suffix == ".pdf":
        print(f"📄 Processing PDF: {file.name}...")
        
        # 1. Selalu jalankan PyMuPDF pertama untuk kecepatan maksimal
        final_text = extract_with_pymupdf(str(file))
        loader_used = "pymupdf"
        
        # 2. Fallback ke LiteParse jika teks terlalu sedikit / gibberish
        if len(final_text) < min_text_length or is_gibberish(final_text):
            print(f"   ⚠️ PyMuPDF kurang optimal ({len(final_text)} chars). Mencoba liteParse...")
            fallback_text = extract_with_liteparse(str(file))
            if len(fallback_text) > 50 and not is_gibberish(fallback_text):
                final_text = fallback_text
                loader_used = "liteparse"
        
        # 3. Evaluasi terakhir: Apakah masih butuh OCR (Docling)? Docling pilihan terakhir.
        if len(final_text) < min_text_length or is_gibberish(final_text):
            if is_gibberish(final_text):
                print(f"   ⚠️ Terdeteksi teks Gibberish/Corrupt ({len(final_text)} chars). Memaksa Docling OCR dinonaktifkan sementara karena memori tidak cukup (OOM).")
            else:
                print(f"   ⚠️ Teks terlalu sedikit ({len(final_text)} chars). Terdeteksi PDF Scan. Pindah ke Docling OCR (Pilihan Terakhir)...")
                
            # Fallback ke Docling OCR (DISABLED TO PREVENT OOM)
            # ocr_text = extract_with_docling(str(file))
            ocr_text = ""
            
            # Gunakan hasil Docling asalkan dia mengembalikan sesuatu yang cukup
            if len(ocr_text.strip()) > 50:
                final_text = ocr_text
                loader_used = "docling_ocr"

        if not final_text.strip():
            print(f"   ❌ Failed to extract: {file.name}")
            return None

        print(f"   ✅ Done ({loader_used}). Length: {len(final_text)} chars.")
        
        metadata = {"source": file.name, "file_type": "pdf", "loader": loader_used}
        return LlamaDocument(text=final_text, metadata=metadata)

    # -------- TXT --------
    elif suffix == ".txt":
        try:
            with open(file, 'r', encoding='utf-8') as f:
                text = f.read()
            if text.strip():
                metadata = {"source": file.name, "file_type": "txt", "loader": "builtin"}
                return LlamaDocument(text=text.strip(), metadata=metadata)
        except Exception as e:
            print(f"❌ Failed to load TXT {file.name}: {e}")
        return None

    # -------- WORD (.docx / .doc) --------
    elif suffix in WORD_EXTENSIONS:
        print(f"📝 Processing Word file: {file.name}...")
        text = extract_word(str(file))
        if not text.strip():
            print(f"   ❌ Failed to extract: {file.name}")
            return None
            
        print(f"   ✅ Done (python-docx). Length: {len(text)} chars.")
        
        metadata = {"source": file.name, "file_type": "docx", "loader": "python-docx"}
        return LlamaDocument(text=text, metadata=metadata)

    # -------- IMAGE --------
    elif suffix in IMAGE_EXTENSIONS:
        print(f"🖼️ Processing image: {file.name}...")
        text = extract_image(str(file))
        if not text.strip():
            print(f"   ❌ No text extracted from image: {file.name}")
            return None
            
        print(f"   ✅ Done (OCR). Length: {len(text)} chars.")
        
        metadata = {"source": file.name, "file_type": "image", "loader": "ocr"}
        return LlamaDocument(text=text, metadata=metadata)
        
    # -------- AUDIO --------
    elif suffix in AUDIO_EXTENSIONS:
        print(f"🎵 Processing audio: {file.name}...")
        text = extract_audio(str(file))
        if not text.strip():
            print(f"   ❌ No text transcribed from audio: {file.name}")
            return None
        metadata = {"source": file.name, "file_type": "audio", "loader": "whisper"}
        return LlamaDocument(text=text, metadata=metadata)
        
    # -------- PPT --------
    elif suffix in PPT_EXTENSIONS:
        print(f"📊 Processing PPT: {file.name}...")
        text = extract_ppt(str(file))
        if not text.strip():
            print(f"   ❌ No text extracted from PPT: {file.name}")
            return None
        metadata = {"source": file.name, "file_type": "ppt", "loader": "python-pptx"}
        return LlamaDocument(text=text, metadata=metadata)
        
    # -------- EXCEL --------
    elif suffix in EXCEL_EXTENSIONS:
        print(f"📈 Processing Excel: {file.name}...")
        if suffix == ".csv":
            try:
                import pandas as pd
                text = f"### CSV Data\n\n{pd.read_csv(str(file)).to_markdown(index=False)}"
            except Exception as e:
                text = ""
                print(f"   ❌ CSV error: {e}")
        else:
            text = extract_excel(str(file))
            
        if not text.strip():
            print(f"   ❌ No text extracted from Spreadsheet: {file.name}")
            return None
        metadata = {"source": file.name, "file_type": "excel", "loader": "pandas"}
        return LlamaDocument(text=text, metadata=metadata)

    else:
        print(f"⏭️ Skipping unsupported file type: {file.name}")
        return None

# -------------------------
# MAIN LOADER — load all docs in a directory
# -------------------------
def load_documents(docs_path: str, min_text_length: int = 300):
    documents = []
    base_path = Path(docs_path)

    if not base_path.exists():
        print(f"⚠️ Path not found: {docs_path}")
        return documents

    for file in base_path.rglob('*'):
        if not file.is_file():
            continue
            
        try:
            relative_path = file.relative_to(base_path)
            if len(relative_path.parts) > 1:
                folder_name = relative_path.parts[0]
            else:
                folder_name = "general"
        except ValueError:
            folder_name = "general"

        doc = load_single_document(str(file), min_text_length)
        if doc:
            file_stat = file.stat()
            # Enrich metadata for filtering
            doc.metadata["collection"] = folder_name.capitalize()
            doc.metadata["relative_path"] = str(relative_path).replace("\\", "/")
            doc.metadata["file_size_kb"] = round(file_stat.st_size / 1024, 2)
            doc.metadata["last_modified"] = datetime.datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            documents.append(doc)

    return documents