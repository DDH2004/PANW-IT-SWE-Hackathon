from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.db import get_db
from backend.models.setting import Setting

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingIn(BaseModel):
    value: str


class SettingOut(BaseModel):
    key: str
    value: str

    class Config:
        from_attributes = True


@router.get("/{key}", response_model=SettingOut)
def get_setting(key: str, db: Session = Depends(get_db)):
    obj = db.query(Setting).filter(Setting.key == key).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Setting not found")
    return obj


@router.put("/{key}", response_model=SettingOut)
def upsert_setting(key: str, payload: SettingIn, db: Session = Depends(get_db)):
    obj = db.query(Setting).filter(Setting.key == key).first()
    if not obj:
        obj = Setting(key=key, value=payload.value)
        db.add(obj)
    else:
        obj.value = payload.value
    db.commit()
    db.refresh(obj)
    return obj
