"""models/portfolio.py — Portfolio and Holding ORM models for PMRI India."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id:         Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:    Mapped[uuid.UUID]    = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    org_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id", ondelete="SET NULL"), nullable=True)
    name:       Mapped[str]          = mapped_column(String(128), nullable=False, default="My Portfolio")
    status:     Mapped[str]          = mapped_column(String(20), nullable=False, default="ACTIVE") # ACTIVE, ARCHIVED
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user     = relationship("User",    back_populates="portfolios")
    org      = relationship("Org",     back_populates="portfolios")
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    quotes   = relationship("Quote",   back_populates="portfolio")


class Holding(Base):
    __tablename__ = "holdings"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False)
    # Canonical form: SYMBOL.NSE or SYMBOL.BSE
    symbol:       Mapped[str]       = mapped_column(String(32), nullable=False)
    exchange:     Mapped[str]       = mapped_column(String(8), nullable=False, default="NSE")
    quantity:     Mapped[float]     = mapped_column(Float, nullable=False)
    created_at:   Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    portfolio = relationship("Portfolio", back_populates="holdings")
