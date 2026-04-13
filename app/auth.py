import os
import secrets
import uuid
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac
from pathlib import Path
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models
from .database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 8)))
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
PASSWORD_SCHEME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390000

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    salt_b64 = b64encode(salt).decode("ascii")
    digest_b64 = b64encode(digest).decode("ascii")
    return f"{PASSWORD_SCHEME}${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split("$", 3)
        if len(parts) != 4:
            return False
        scheme, iterations_str, salt_b64, digest_b64 = parts
        if scheme != PASSWORD_SCHEME:
            return False
        iterations = int(iterations_str)
        salt = b64decode(salt_b64.encode("ascii"))
        expected_digest = b64decode(digest_b64.encode("ascii"))
        actual_digest = pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return secrets.compare_digest(actual_digest, expected_digest)
    except Exception:
        return False


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return sub
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def _extract_token(request: Request) -> Optional[str]:
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()
    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_email = decode_token(token)
    user = db.query(models.User).filter(models.User.email == user_email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_optional_user(request: Request, db: Session) -> Optional[models.User]:
    token = _extract_token(request)
    if not token:
        return None
    try:
        user_email = decode_token(token)
    except HTTPException:
        return None
    return db.query(models.User).filter(models.User.email == user_email).first()


def get_admin_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def save_upload_file(upload_dir: str, filename: str, file_bytes: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds 5MB limit")
    safe_name = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(upload_dir, exist_ok=True)
    target_path = os.path.join(upload_dir, safe_name)
    with open(target_path, "wb") as f:
        f.write(file_bytes)
    return f"/uploads/{safe_name}"

