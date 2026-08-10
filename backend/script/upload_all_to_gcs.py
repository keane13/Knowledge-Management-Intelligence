import os
from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account

DOCS_PATH = r"C:\Users\keane\Desktop\Portofolio\Top 5\rag_pro_v3\data\knowledge\documents"
GCS_SERVICE_ACCOUNT_FILE = r"C:\Users\keane\Desktop\Portofolio\Top 5\rag_pro_v3\backend\data\storage_key\smooth-reason-491707-f6-c122abd4eafb.json"
GCS_BUCKET_NAME = "knowledge-kmi"

def upload_all_files():
    base_path = Path(DOCS_PATH)
    if not base_path.exists():
        print(f"Directory {DOCS_PATH} does not exist.")
        return

    try:
        credentials = service_account.Credentials.from_service_account_file(GCS_SERVICE_ACCOUNT_FILE)
        client = storage.Client(credentials=credentials, project=credentials.project_id)
        bucket = client.bucket(GCS_BUCKET_NAME)
    except Exception as e:
        print(f"Failed to initialize GCS client: {e}")
        return

    upload_count = 0
    for p in base_path.rglob('*'):
        if p.is_file():
            # Get relative path for the blob name (e.g., finance/report.pdf)
            blob_name = p.relative_to(base_path).as_posix()
            try:
                blob = bucket.blob(blob_name)
                print(f"Uploading {p} to gs://{GCS_BUCKET_NAME}/{blob_name}...")
                blob.upload_from_filename(str(p))
                upload_count += 1
            except Exception as e:
                print(f"Failed to upload {p}: {e}")

    print(f"Successfully uploaded {upload_count} files to GCS.")

if __name__ == "__main__":
    upload_all_files()
