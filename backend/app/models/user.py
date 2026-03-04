"""models/user.py — User ORM model for PMRI India."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id:              Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email:           Mapped[str]       = mapped_column(String(254), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str]       = mapped_column(String(256), nullable=False)
    is_admin:        Mapped[bool]      = mapped_column(Boolean, default=False)
    # RETAIL | INSTITUTIONAL_BASIC | INSTITUTIONAL_PREMIUM
    tier:            Mapped[str]       = mapped_column(String(32), default="RETAIL", nullable=False)
    created_at:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    org_memberships = relationship("OrgMember", back_populates="user", cascade="all, delete-orphan")
    portfolios      = relationship("Portfolio", back_populates="user")
    quotes          = relationship("Quote", back_populates="user")
    policies        = relationship("Policy", back_populates="user")
