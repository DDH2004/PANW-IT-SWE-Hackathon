from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.db import get_db
from backend.models.user import User
from backend.models.session_token import SessionToken
from backend.utils.auth import hash_password, verify_password, create_token

router = APIRouter()

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post('/auth/register')
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail='Username already exists')
    u = User(username=body.username, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return { 'id': u.id, 'username': u.username }

@router.post('/auth/login')
async def login(body: LoginRequest, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == body.username).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    t = create_token()
    tok = SessionToken(token=t, user_id=u.id)
    db.add(tok)
    db.commit()
    return { 'token': t, 'user': { 'id': u.id, 'username': u.username } }