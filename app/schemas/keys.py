from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class KeyCreateRequest(BaseModel):
    type: str
    note: Optional[str] = None

class KeyUpdateRequest(BaseModel):
    is_active: Optional[bool] = None
    note: Optional[str] = None

class KeyResponse(BaseModel):
    key_value: str
    is_active: bool
    created_at: datetime
    expired_at: Optional[datetime] = None
    note: Optional[str] = None
    machine_name: Optional[str] = None
    os_version: Optional[str] = None
    revit_version: Optional[str] = None
    cpu_info: Optional[str] = None
    ip_address: Optional[str] = None
    machine_hash: Optional[str] = None
    last_check: Optional[datetime] = None

class KeyValidateRequest(BaseModel):
    key_value: str
    machine_name: Optional[str] = None
    os_version: Optional[str] = None
    revit_version: Optional[str] = None
    cpu_info: Optional[str] = None
    ip_address: Optional[str] = None
    machine_hash: Optional[str] = None
