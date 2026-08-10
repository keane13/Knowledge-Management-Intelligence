from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
import bcrypt
from datetime import timedelta

from src.infrastructure.database import SessionLocal, User as DBUser
from src.infrastructure.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from pydantic import BaseModel

router = APIRouter(tags=["Auth"])

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

@router.post("/register")
def register(user: UserRegister):
    db: Session = SessionLocal()
    try:
        existing_user = db.query(DBUser).filter(DBUser.username == user.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
            
        hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_user = DBUser(username=user.username, password_hash=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": new_user.username}, expires_delta=access_token_expires
        )
        return {"message": "User registered successfully", "id": new_user.id, "token": access_token}
    finally:
        db.close()

@router.post("/login")
def login(user: UserLogin):
    db: Session = SessionLocal()
    try:
        db_user = db.query(DBUser).filter(DBUser.username == user.username).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="Incorrect username or password")
            
        if not bcrypt.checkpw(user.password.encode('utf-8'), db_user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.username}, expires_delta=access_token_expires
        )
        return {"message": "Login successful", "id": db_user.id, "username": db_user.username, "token": access_token}
    finally:
        db.close()
