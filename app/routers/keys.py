from datetime import datetime, timedelta
import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..schemas.keys import KeyCreateRequest, KeyUpdateRequest, KeyResponse, KeyValidateRequest
from ..models.key_record import KeyRecord
from ..dependencies import admin_required

router = APIRouter(prefix="/keys", tags=["keys"]) 


def _expiry_for_type(t: str) -> datetime | None:
    t = t.lower().strip()
    if t == "trial":
        return datetime.utcnow() + timedelta(days=7)
    if t == "month":
        return datetime.utcnow() + timedelta(days=30)
    if t == "year":
        return datetime.utcnow() + timedelta(days=365)
    if t == "lifetime":
        return datetime.utcnow() + timedelta(days=365*1000)
    raise HTTPException(status_code=400, detail="Invalid type: must be trial/month/year/lifetime")


def _generate_key() -> str:
    return secrets.token_urlsafe(24)


@router.post("/create", response_model=KeyResponse, dependencies=[Depends(admin_required)])
def create_key(payload: KeyCreateRequest, db: Session = Depends(get_db)):
    key_value = _generate_key()
    record = KeyRecord(
        key_value=key_value,
        is_active=True,
        expired_at=_expiry_for_type(payload.type),
        note=payload.note,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return KeyResponse(**record.__dict__)


@router.get("/list", response_model=List[KeyResponse], dependencies=[Depends(admin_required)])
def list_keys(db: Session = Depends(get_db)):
    records = db.query(KeyRecord).order_by(KeyRecord.id.desc()).all()
    return [KeyResponse(**r.__dict__) for r in records]


@router.get("/{key_value}", response_model=KeyResponse, dependencies=[Depends(admin_required)])
def get_key(key_value: str, db: Session = Depends(get_db)):
    record = db.query(KeyRecord).filter(KeyRecord.key_value == key_value).first()
    if not record:
        raise HTTPException(status_code=404, detail="Key not found")
    return KeyResponse(**record.__dict__)


@router.put("/{key_value}", response_model=KeyResponse, dependencies=[Depends(admin_required)])
def update_key(key_value: str, payload: KeyUpdateRequest, db: Session = Depends(get_db)):
    record = db.query(KeyRecord).filter(KeyRecord.key_value == key_value).first()
    if not record:
        raise HTTPException(status_code=404, detail="Key not found")
    if payload.is_active is not None:
        record.is_active = payload.is_active
    if payload.note is not None:
        record.note = payload.note
    db.commit()
    db.refresh(record)
    return KeyResponse(**record.__dict__)


@router.delete("/{key_value}", dependencies=[Depends(admin_required)])
def delete_key(key_value: str, db: Session = Depends(get_db)):
    record = db.query(KeyRecord).filter(KeyRecord.key_value == key_value).first()
    if not record:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(record)
    db.commit()
    return {"detail": "Deleted"}


@router.post("/validate")
def validate(payload: KeyValidateRequest, db: Session = Depends(get_db)):
    record = db.query(KeyRecord).filter(
        KeyRecord.key_value == payload.key_value
    ).first()

    # Không tìm thấy key
    if not record:
        return {
            "valid": False,
            "is_active": False,
            "expired_at": None,
            "note": "Key not found"
        }

    # Key bị khóa (is_active = false)
    if not record.is_active:
        return {
            "valid": False,
            "is_active": False,
            "expired_at": record.expired_at,
            "note": "Key is locked"
        }

    # Key hết hạn
    if record.expired_at and record.expired_at < datetime.utcnow():
        return {
            "valid": False,
            "is_active": True,
            "expired_at": record.expired_at,
            "note": "Key expired"
        }

    # Update thông tin máy
    record.machine_name = payload.machine_name or record.machine_name
    record.os_version = payload.os_version or record.os_version
    record.revit_version = payload.revit_version or record.revit_version
    record.cpu_info = payload.cpu_info or record.cpu_info
    record.ip_address = payload.ip_address or record.ip_address

    # Ghi machine_hash nếu chưa có — tránh override lần sau
    if not record.machine_hash:
        record.machine_hash = payload.machine_hash

    record.last_check = datetime.utcnow()
    db.commit()

    # Trả về thông tin key hợp lệ
    return {
        "valid": True,
        "is_active": True,
        "expired_at": record.expired_at,
        "machine_hash": record.machine_hash,
        "note": record.note or "Valid license"
    }