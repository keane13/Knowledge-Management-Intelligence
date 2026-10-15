import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Set JWT_SECRET_KEY in production (Secret Manager on Cloud Run); the fallback is for local dev only
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "my_super_secret_key_for_rag_pro")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Comma-separated usernames allowed to delete documents / re-index the knowledge base.
# Unset locally = any logged-in user; unset on Cloud Run = nobody (fail closed).
ADMIN_USERS = {u.strip() for u in os.environ.get("ADMIN_USERS", "").split(",") if u.strip()}

def require_admin(username: str = Depends(get_current_user)):
    if ADMIN_USERS:
        allowed = username in ADMIN_USERS
    else:
        allowed = os.environ.get("CLOUD_RUN") != "1"
    if not allowed:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return username
