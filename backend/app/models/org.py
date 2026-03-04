"""models/org.py — Org + OrgMember ORM models for PMRI India."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Org(Base):
    __tablename__ = "orgs"

    id:         Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name:       Mapped[str]       = mapped_column(String(128), unique=True, nullable=False)
    # INSTITUTIONAL_BASIC | INSTITUTIONAL_PREMIUM
    tier:       Mapped[str]       = mapped_column(String(32), default="INSTITUTIONAL_BASIC", nullable=False)
    created_at: Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    members    = relationship("OrgMember", back_populates="org", cascade="all, delete-orphan")
    portfolios = relationship("Portfolio", back_populates="org")
    quotes     = relationship("Quote", back_populates="org")
    policies   = relationship("Policy", back_populates="org")


class OrgMember(Base):
    __tablename__ = "org_members"

    org_id:  Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    # OWNER | MEMBER
    role:    Mapped[str]       = mapped_column(String(16), default="MEMBER", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    org  = relationship("Org",  back_populates="members")
    user = relationship("User", back_populates="org_memberships")
