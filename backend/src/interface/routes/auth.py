import re
import uuid
import datetime
from datetime import timedelta

import bcrypt
from fastapi import APIRouter, HTTPException
from google.api_core.exceptions import AlreadyExists
from pydantic import BaseModel

from src.infrastructure.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.infrastructure.firestore_client import get_firestore_client

router = APIRouter(tags=["Auth"])

# Users live in Firestore (collection "users", document id = username) so accounts
# survive Cloud Run restarts and are shared across instances.
USERS_COLLECTION = "users"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@+-]{3,128}$")  # usernames are usually emails
MIN_PASSWORD_LENGTH = 8

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

def _validate_username(username: str) -> str:
    username = username.strip()
    # Firestore document ids may not be '.', '..' or match __.*__
    if not USERNAME_RE.match(username) or (username.startswith("__") and username.endswith("__")) or set(username) == {"."}:
        raise HTTPException(
            status_code=422,
            detail="Username must be 3-128 characters: letters, digits or _ . @ + -",
        )
    return username

def _issue_token(username: str) -> str:
    return create_access_token(
        data={"sub": username}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

@router.post("/register")
def register(user: UserRegister):
    username = _validate_username(user.username)
    if len(user.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=422, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    if len(user.password.encode("utf-8")) > 72:
        raise HTTPException(status_code=422, detail="Password must be at most 72 bytes")

    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = str(uuid.uuid4())
    try:
        # create() fails atomically if the username is already taken
        get_firestore_client().collection(USERS_COLLECTION).document(username).create({
            "id": user_id,
            "username": username,
            "password_hash": hashed_password,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
    except AlreadyExists:
        raise HTTPException(status_code=400, detail="Username already registered")

    return {"message": "User registered successfully", "id": user_id, "token": _issue_token(username)}

@router.post("/login")
def login(user: UserLogin):
    username = user.username.strip()
    doc = None
    if USERNAME_RE.match(username):
        doc = get_firestore_client().collection(USERS_COLLECTION).document(username).get()
    if doc is None or not doc.exists:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    data = doc.to_dict()
    password_bytes = user.password.encode('utf-8')
    if len(password_bytes) > 72 or not bcrypt.checkpw(password_bytes, data["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    return {"message": "Login successful", "id": data.get("id"), "username": username, "token": _issue_token(username)}
