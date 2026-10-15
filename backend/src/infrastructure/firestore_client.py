import os
import datetime
import logging
from google.cloud import firestore

logger = logging.getLogger(__name__)

FIRESTORE_DB_NAME = "knowldege-mi"

def get_firestore_client():
    """
    Returns an initialized Firestore client.
    """
    try:
        # Assuming the key is at the root backend directory or data directory
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        key_path = os.path.join(BASE_DIR, "data", "firestore-key", "smooth-reason-491707-f6-b520a2342766.json")
        
        if os.path.exists(key_path):
            client = firestore.Client.from_service_account_json(
                key_path,
                database=FIRESTORE_DB_NAME
            )
        else:
            # Fallback to default credentials if file is missing (e.g. deployed to Cloud Run)
            client = firestore.Client(database=FIRESTORE_DB_NAME)
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")
        raise e

def user_docs_sorted(collection_ref, user_id: str, limit: int = 50):
    """
    Documents in collection_ref owned by user_id, newest first.
    Sorted in Python so no composite (user_id, timestamp) index is required.
    """
    from google.cloud.firestore_v1.base_query import FieldFilter
    docs = list(collection_ref.where(filter=FieldFilter("user_id", "==", user_id)).stream())
    epoch = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    def _ts(doc):
        ts = (doc.to_dict() or {}).get("timestamp")
        if not isinstance(ts, datetime.datetime):
            return epoch
        return ts if ts.tzinfo else ts.replace(tzinfo=datetime.timezone.utc)

    docs.sort(key=_ts, reverse=True)
    return docs[:limit]
