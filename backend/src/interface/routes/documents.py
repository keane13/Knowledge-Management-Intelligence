import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pathlib import Path

from src.infrastructure.auth import get_current_user, require_admin
from src.infrastructure.config.configs import DOCS_PATH
from src.application.rag.loader import load_single_document, IMAGE_EXTENSIONS, WORD_EXTENSIONS, AUDIO_EXTENSIONS, PPT_EXTENSIONS, EXCEL_EXTENSIONS
from src.application.rag.vectorstore import get_weaviate_client
from src.infrastructure.llm.llm import generate_answer, DEFAULT_TEXT_MODEL

try:
    from weaviate.classes.query import Filter
except ImportError:
    Filter = None

from google.cloud import storage
from google.oauth2 import service_account

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
GCS_SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, "data", "storage_key", "smooth-reason-491707-f6-c122abd4eafb.json")
GCS_BUCKET_NAME = "knowledge-kmi"

ALLOWED_EXTENSIONS = {'.pdf', '.txt'} | WORD_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | PPT_EXTENSIONS | EXCEL_EXTENSIONS

router = APIRouter(tags=["Documents"])

def _safe_doc_path(relative_name: str) -> tuple[str, str]:
    """Resolve a user-supplied name inside DOCS_PATH.

    Returns (absolute_path, normalized_relative_name). Rejects anything that escapes
    DOCS_PATH (e.g. '../', absolute paths, drive letters).
    """
    root = os.path.realpath(DOCS_PATH)
    if not relative_name or os.path.isabs(relative_name) or "\x00" in relative_name:
        raise HTTPException(status_code=400, detail="Invalid filename")
    full_path = os.path.realpath(os.path.join(root, relative_name))
    try:
        inside = os.path.commonpath([root, full_path]) == root and full_path != root
    except ValueError:  # different drives on Windows
        inside = False
    if not inside:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return full_path, os.path.relpath(full_path, root).replace(os.sep, "/")

def _index_file(file_path: str) -> int:
    """Extract, split, and upsert a single file into Weaviate. Returns chunk count."""
    doc = load_single_document(file_path)
    if not doc:
        return 0
        
    from llama_index.core.node_parser import SemanticSplitterNodeParser
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from src.application.rag.vectorstore import get_vectorstore
    
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
    )
    
    nodes = splitter.get_nodes_from_documents([doc])
    if not nodes:
        return 0
        
    for node in nodes:
        node.embedding = None
        
    vectorstore = get_vectorstore()
    vectorstore.add(nodes)
    
    return len(nodes)

def _gcs_client():
    if os.path.exists(GCS_SERVICE_ACCOUNT_FILE):
        credentials = service_account.Credentials.from_service_account_file(GCS_SERVICE_ACCOUNT_FILE)
        return storage.Client(credentials=credentials, project=credentials.project_id)
    return storage.Client()

@router.get("/files")
def list_files(current_user: str = Depends(get_current_user)):
    try:
        client = _gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blobs = bucket.list_blobs()
        files = []
        for blob in blobs:
            files.append({
                "filename": blob.name,
                "size": blob.size,
                "updated": blob.updated.isoformat() if blob.updated else None
            })
        return {"files": files}
    except Exception as e:
        print(f"Error fetching from GCS: {e}")
        return {"files": []}

from fastapi.responses import FileResponse

def _ensure_local(file_path: str, filename: str) -> None:
    """Download the file from GCS if it's missing locally (e.g. fresh Cloud Run instance)."""
    if os.path.exists(file_path):
        return
    try:
        blob = _gcs_client().bucket(GCS_BUCKET_NAME).blob(filename)
        if not blob.exists():
            raise HTTPException(status_code=404, detail="File not found locally or in GCS")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        blob.download_to_filename(file_path)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error downloading {filename} from GCS: {e}")
        raise HTTPException(status_code=404, detail="File not found")

@router.get("/files/{filename:path}/content")
async def get_file_content(filename: str, current_user: str = Depends(get_current_user)):
    """Serve the raw file content for previewing in the UI."""
    file_path, filename = _safe_doc_path(filename)
    _ensure_local(file_path, filename)
    return FileResponse(file_path)

@router.delete("/files/{filename:path}")
async def delete_file(filename: str, current_user: str = Depends(require_admin)):
    """Delete a file from storage and its associated chunks from Weaviate."""
    file_path, filename = _safe_doc_path(filename)
    
    # 1. Delete from local cache and GCS (the source of truth on Cloud Run)
    deleted = False
    if os.path.exists(file_path):
        os.remove(file_path)
        deleted = True
    try:
        blob = _gcs_client().bucket(GCS_BUCKET_NAME).blob(filename)
        if blob.exists():
            blob.delete()
            deleted = True
    except Exception as e:
        print(f"❌ Error deleting {filename} from GCS: {e}")
    if not deleted:
        raise HTTPException(status_code=404, detail="File not found")

    # 2. Delete from Weaviate
    try:
        client = get_weaviate_client()
        if Filter:
            collection = client.collections.get("KnowledgeBase")
            collection.data.delete_many(
                where=Filter.by_property("source").equal(filename)
            )
        return {"message": f"Successfully deleted {filename} and its indexed content."}
    except Exception as e:
        print(f"❌ Error deleting {filename} from Weaviate: {e}")
        return {"message": f"Deleted local file {filename}, but failed to clear vector store: {e}"}

@router.post("/files/{filename:path}/summarize")
async def summarize_file(filename: str, current_user: str = Depends(get_current_user)):
    """Generate a summary for a specific document."""
    file_path, filename = _safe_doc_path(filename)
    _ensure_local(file_path, filename)
        
    try:
        doc = load_single_document(file_path)
        if not doc:
            raise HTTPException(status_code=400, detail="Could not extract text from document")
            
        summary_prompt = (
            "You are an expert document analyst and summarizer. "
            "Please provide a polished, well-structured summary of the document below in Markdown format. "
            "IMPORTANT: Use the SAME LANGUAGE as the document (e.g., if the document is in Indonesian, write the summary in Indonesian; if in English, write in English).\n\n"
            "Guidelines:\n"
            "1. Start with a brief overview (Abstract/Executive Summary).\n"
            "2. Use bullet points for key findings or main sections.\n"
            "3. Use bold text for important terms or figures.\n"
            "4. Ensure the tone is professional and the writing is clear and 'dirapikan' (polished).\n\n"
            f"DOCUMENT CONTENT ({filename}):\n"
            "--------------------\n"
            f"{doc.page_content[:12000]}"
        )
        
        summary = generate_answer(
            messages=[{"role": "user", "content": summary_prompt}],
            model_key=DEFAULT_TEXT_MODEL
        )
        
        return {"filename": filename, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), folder: str = Form(None), current_user: str = Depends(get_current_user)):
    """Upload a file and immediately index it into the Weaviate vector store."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Use the folder if provided, else root. Never trust client-supplied path segments.
    safe_name = os.path.basename((file.filename or "").replace("\\", "/"))
    target_filename = f"{folder.strip()}/{safe_name}" if folder and folder.strip() else safe_name
    file_path, target_filename = _safe_doc_path(target_filename)

    # Ensure local directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        chunks_indexed = _index_file(file_path)
    except Exception as e:
        print(f"❌ Indexing error for {file.filename}: {e}")
        chunks_indexed = 0

    # Upload to Google Cloud Storage
    gcs_url = None
    try:
        client = _gcs_client()
        bucket = client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(target_filename)
        blob.upload_from_filename(file_path)
        gcs_url = f"gs://{GCS_BUCKET_NAME}/{target_filename}"
        print(f"✅ Uploaded to GCS: {gcs_url}")
    except Exception as e:
        print(f"❌ Error uploading to GCS: {e}")

    if chunks_indexed == 0:
        return {
            "filename": file.filename,
            "file_type": ext.lstrip("."),
            "chunks_indexed": 0,
            "gcs_url": gcs_url,
            "message": "File saved but no text could be extracted for indexing.",
        }

    return {
        "filename": file.filename,
        "file_type": ext.lstrip("."),
        "chunks_indexed": chunks_indexed,
        "gcs_url": gcs_url,
        "message": f"File uploaded, indexed successfully ({chunks_indexed} chunks), and saved to GCS.",
    }

@router.post("/index")
async def reindex_all(current_user: str = Depends(require_admin)):
    """Manually trigger a full re-index of all documents in the docs folder."""
    from src.application.rag.loader import load_documents
    from llama_index.core.node_parser import SemanticSplitterNodeParser
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from src.application.rag.vectorstore import get_vectorstore, get_weaviate_client

    docs = load_documents(DOCS_PATH)
    if not docs:
        return {"message": "No documents found to index.", "chunks_indexed": 0}

    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
    )
    
    nodes = splitter.get_nodes_from_documents(docs)
    for node in nodes:
        node.embedding = None
    
    client = get_weaviate_client()
    client.collections.delete_all()

    vectorstore = get_vectorstore()
    vectorstore.add(nodes)
    return {"message": f"Re-indexed {len(docs)} documents into {len(nodes)} chunks.", "chunks_indexed": len(nodes)}
