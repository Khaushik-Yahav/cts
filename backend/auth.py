from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from backend.db import db_session
from backend.models import User


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
return pwd_context.verify(password, hashed)


# JWT settings
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "60"))


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class AuthUser:
def __init__(self, id: str, email: str):
self.id = id
self.email = email


def create_access_token(user_id: str, email: str, expires_delta: Optional[timedelta] = None) -> str:
to_encode = {"sub": user_id, "email": email, "iat": datetime.utcnow()}
expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
to_encode.update({"exp": expire})
return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> AuthUser:
credentials_exception = HTTPException(
status_code=status.HTTP_401_UNAUTHORIZED,
detail="Could not validate credentials",
headers={"WWW-Authenticate": "Bearer"},
)
try:
payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
user_id: str = payload.get("sub")
email: str = payload.get("email")
if user_id is None or email is None:
raise credentials_exception
except JWTError:
raise credentials_exception


with db_session() as db:
user = db.get(User, user_id)
if not user or user.email != email:
raise credentials_exception
return AuthUser(id=user.id, email=user.email)