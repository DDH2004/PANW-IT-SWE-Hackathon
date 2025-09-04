import os, hmac, hashlib, secrets
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.user import User
from backend.models.session_token import SessionToken

_SCHEME = HTTPBearer(auto_error=False)
PEPPER = os.getenv('AUTH_PEPPER', 'pepper123')

def hash_password(password: str) -> str:
    salt = secrets.token_hex(8)
    digest = hashlib.sha256((salt + PEPPER + password).encode()).hexdigest()
    return f"{salt}${digest}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split('$', 1)
    except ValueError:
        return False
    calc = hashlib.sha256((salt + PEPPER + password).encode()).hexdigest()
    return hmac.compare_digest(calc, digest)

def create_token() -> str:
    return secrets.token_urlsafe(40)

def get_current_user(db: Session = Depends(get_db), creds: HTTPAuthorizationCredentials = Depends(_SCHEME)) -> User:
    if not creds or creds.scheme.lower() != 'bearer':
        raise HTTPException(status_code=401, detail='Missing auth token')
    row = db.query(SessionToken).filter(SessionToken.token == creds.credentials).first()
    if not row:
        raise HTTPException(status_code=401, detail='Invalid token')
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')
    return user
