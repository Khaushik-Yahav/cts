from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship
import enum


Base = declarative_base()


class RoleEnum(str, enum.Enum):
user = "user"
assistant = "assistant"


class DocType(str, enum.Enum):
knowledge = "knowledge" # global KB doc
prescription = "prescription" # private per-user doc


class User(Base):
__tablename__ = "users"
id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
email = Column(String, unique=True, index=True, nullable=False)
password_hash = Column(String, nullable=False)
created_at = Column(DateTime, default=datetime.utcnow)


sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")


class ChatSession(Base):
__tablename__ = "chat_sessions"


id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
title = Column(String, default="New chat")
summary = Column(Text, default="") # rolling summary of earlier turns
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow)


user = relationship("User", back_populates="sessions")
messages = relationship(
"Message",
back_populates="session",
cascade="all, delete-orphan",
order_by="Message.created_at",
)


class Message(Base):
__tablename__ = "messages"


id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"))
role = Column(Enum(RoleEnum), nullable=False)
content = Column(Text, nullable=False)
citations = Column(JSONB, nullable=True)
created_at = Column(DateTime, default=datetime.utcnow)


session = relationship("ChatSession", back_populates="messages")


class Document(Base):
owner = relationship("User", back_populates="documents")