import json
import re
import traceback
import pandas as pd
import os
from io import BytesIO, StringIO
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
from src.infrastructure.auth import get_current_user
from src.infrastructure.llm.llm import generate_answer
from google.cloud import bigquery
from google.oauth2 import service_account
from src.infrastructure.auth import get_current_user
from src.infrastructure.llm.llm import generate_answer
from google.cloud import firestore
import datetime
import uuid
from src.infrastructure.firestore_client import get_firestore_client

router = APIRouter(prefix="/data-analysis", tags=["Data Analysis"])

class BigQueryAnalyzeRequest(BaseModel):
    dataset_id: str
    table_id: str

def _analyze_dataframe(df: pd.DataFrame, title: str, user_id: str):
    # Limit to max 50 rows for LLM context, but stats are on full data
    stats = df.describe(include='all').to_json()
    info_buffer = StringIO()
    df.info(buf=info_buffer)
    info_str = info_buffer.getvalue()
    head_json = df.head(10).to_json(orient="records")

    system_prompt = (
        "Anda adalah asisten Data Analyst AI tingkat lanjut. "
        "Anda akan diberikan statistik ringkasan, info dataset, dan beberapa sampel baris dari file data yang diunggah pengguna. "
        "Tugas Anda adalah menghasilkan laporan analisis JSON terstruktur.\n\n"
        "WAJIB KEMBALIKAN OUTPUT DALAM FORMAT JSON VALID BERIKUT (Tanpa blok kode Markdown seperti ```json):\n"
        "{\n"
        '  "narration": "Narasi insight mendalam tentang data ini dalam bahasa Indonesia.",\n'
        '  "statistical_summary": "Ringkasan statistik penting dari data (misal distribusi, rata-rata kunci) dalam teks.",\n'
        '  "analyses": [\n'
        '    {\n'
        '      "question": "Pertanyaan analisis mendalam 1 dari data?",\n'
        '      "answer": "Narasi jawaban yang komprehensif untuk pertanyaan 1.",\n'
        '      "chart": {\n'
        '        "analysisType": "univariate",\n'
        '        "chartType": "BarChart", // Pilihan: BarChart, LineChart, PieChart, ScatterChart, Heatmap\n'
        '        "title": "Judul Chart",\n'
        '        "data": [\n'
        '           // WAJIB IKUTI ATURAN KEY BERIKUT BERDASARKAN chartType:\n'
        '           // Jika BarChart/LineChart/PieChart: [{"name": "Label", "value": 10}]\n'
        '           // Jika ScatterChart: [{"x": 10.5, "y": 20.2}]\n'
        '           // Jika Heatmap (korelasi): [{"x": "KolomA", "y": "KolomB", "value": 0.85}]\n'
        '        ]\n'
        '      }\n'
        '    }\n'
        '    // WAJIB BUAT TEPAT 5 ITEM DALAM ARRAY ANALYSES INI\n'
        '  ]\n'
        "}\n\n"
        "Peraturan: Hasilkan TEPAT 5 analisis. Masing-masing analisis harus memiliki chart dengan data yang tidak kosong. "
        "Sangat penting: Anda harus menggunakan nama key (seperti 'name', 'value', 'x', 'y') TEPAT seperti contoh di atas agar chart bisa di-render oleh Recharts."
    )

    user_prompt = (
        f"Dataset Info:\n{info_str}\n\n"
        f"Statistik (JSON):\n{stats}\n\n"
        f"Sampel Baris (JSON):\n{head_json}\n\n"
        "Tolong berikan insight umum, dan 5 pertanyaan analisis spesifik lengkap dengan jawaban narasi dan konfigurasi chart sesuai format JSON."
    )

    messages = [
        {"role": "system", "content": system_prompt}, 
        {"role": "user", "content": user_prompt}
    ]

    # Use a highly capable model for strict JSON adherence
    response_text = generate_answer(messages, stream=False, model_key="llama-3.3-70b-versatile")
    
    # Clean potential markdown and extract JSON block
    response_text = response_text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text, re.IGNORECASE)
    if match:
        response_text = match.group(1).strip()
    else:
        # Fallback: extract substring from first { to last }
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            response_text = response_text[start:end+1]
        
    try:
        result_json = json.loads(response_text)
        
        # Save to Firestore
        try:
            db = get_firestore_client()
            doc_id = str(uuid.uuid4())
            doc_data = {
                "id": doc_id,
                "title": title,
                "timestamp": datetime.datetime.utcnow(),
                "result": result_json,
                "user_id": user_id
            }
            db.collection("data_analysis_history").document(doc_id).set(doc_data)
        except Exception as e:
            print(f"Failed to save data analysis history: {e}")
            
    except json.JSONDecodeError:
        print("Failed to decode JSON from LLM. Raw:", response_text)
        raise HTTPException(status_code=500, detail="Gagal menghasilkan format JSON yang valid dari AI.")

    return result_json

@router.get("/history")
async def list_data_analysis_history(current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        # Ensure we only fetch for current user if applicable, but for now we fetch all or limit
        # The prompt doesn't specify user isolation, so we'll just fetch order by timestamp desc
        docs = db.collection("data_analysis_history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
        
        history = []
        for doc in docs:
            data = doc.to_dict()
            # Only return metadata for list
            history.append({
                "id": doc.id,
                "title": data.get("title", "Untitled Analysis"),
                "timestamp": data.get("timestamp").isoformat() if hasattr(data.get("timestamp"), "isoformat") else str(data.get("timestamp"))
            })
        return history
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{doc_id}")
async def get_data_analysis_history(doc_id: str, current_user: str = Depends(get_current_user)):
    try:
        db = get_firestore_client()
        doc = db.collection("data_analysis_history").document(doc_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="History not found")
        data = doc.to_dict()
        if hasattr(data.get("timestamp"), "isoformat"):
            data["timestamp"] = data["timestamp"].isoformat()
        else:
             data["timestamp"] = str(data.get("timestamp"))
        return data
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_data_file(file: UploadFile = File(...), current_user: str = Depends(get_current_user)):
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(".csv"):
            try:
                df = pd.read_csv(BytesIO(content))
            except Exception:
                # Try with different encoding/separator if first fails
                df = pd.read_csv(BytesIO(content), encoding="ISO-8859-1", sep=";")
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Hanya file .csv, .xls, dan .xlsx yang didukung.")

        return _analyze_dataframe(df, filename, current_user)

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def _get_bq_client():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    key_path = os.path.join(BASE_DIR, "data", "bigquery_key", "smooth-reason-491707-f6-e931aa62cb9b.json")
    if not os.path.exists(key_path):
        raise HTTPException(status_code=500, detail="BigQuery credentials not found.")
    credentials = service_account.Credentials.from_service_account_file(key_path)
    return bigquery.Client(credentials=credentials, project=credentials.project_id)

@router.get("/bigquery/tables")
async def list_bigquery_tables(current_user: str = Depends(get_current_user)):
    try:
        # Pre-defined known datasets from tools.yaml
        datasets = ["knowledge_finance", "knowledge_hr", "knowledge_legal", "knowledge_marketing"]
        
        try:
            client = _get_bq_client()
        except HTTPException:
            # If no BQ configured, just return static list based on our knowledge or empty
            return []

        all_tables = []
        for dataset_id in datasets:
            try:
                tables = client.list_tables(dataset_id)
                for table in tables:
                    all_tables.append({
                        "dataset": dataset_id,
                        "table": table.table_id,
                        "id": f"{dataset_id}.{table.table_id}"
                    })
            except Exception as e:
                print(f"Error fetching tables for dataset {dataset_id}: {e}")
                
        return all_tables
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bigquery/analyze")
async def analyze_bigquery_table(request: BigQueryAnalyzeRequest, current_user: str = Depends(get_current_user)):
    try:
        # Guardrail: Prevent SQL Injection by ensuring valid BigQuery identifiers
        if not re.match(r"^[a-zA-Z0-9_]+$", request.dataset_id) or not re.match(r"^[a-zA-Z0-9_]+$", request.table_id):
            raise HTTPException(status_code=400, detail="Guardrail Blocked: Invalid dataset or table ID format.")

        client = _get_bq_client()
        query = f"SELECT * FROM `{client.project}.{request.dataset_id}.{request.table_id}` LIMIT 1000"
        
        try:
            df = client.query(query).to_dataframe()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Gagal query ke BigQuery: {str(e)}")

        if df.empty:
            raise HTTPException(status_code=400, detail="Tabel kosong.")

        return _analyze_dataframe(df, f"{request.dataset_id}.{request.table_id}", current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
