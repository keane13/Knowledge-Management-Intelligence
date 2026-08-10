from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from src.infrastructure.config.configs import DATABASE_URL
import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(String, primary_key=True)
    title = Column(String, default="New Chat")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('chat_sessions.id'))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    sources = Column(Text, nullable=True) # JSON serialized list of {filename, content}
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

# SQLite needs check_same_thread=False when used with FastAPI's threadpool.
_engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
