from sqlalchemy import Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from ..core.database import Base

class KeyRecord(Base):
    __tablename__ = "key_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key_value: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    machine_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revit_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cpu_info: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    machine_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
