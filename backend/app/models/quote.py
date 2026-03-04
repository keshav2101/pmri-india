"""models/quote.py — Quote and MLInference ORM models for PMRI India."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class MLInference(Base):
    __tablename__ = "ml_inferences"

    id:                 Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_version:      Mapped[str]       = mapped_column(String(64), nullable=False)
    ticker_signals:     Mapped[dict]      = mapped_column(JSON, default=dict, nullable=False)
    portfolio_signals:  Mapped[dict]      = mapped_column(JSON, default=dict, nullable=False)
    tail_loss_prob:     Mapped[float]     = mapped_column(Float, nullable=False)
    predicted_vol:      Mapped[float]     = mapped_column(Float, nullable=False)
    created_at:         Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    quote = relationship("Quote", back_populates="ml_inference", uselist=False)


class Quote(Base):
    __tablename__ = "quotes"

    id:                  Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id:             Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    org_id:              Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=True)
    portfolio_id:        Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)
    ml_inference_id:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("ml_inferences.id"), nullable=True)

    # Term: INTRADAY | WEEKLY | MONTHLY
    term:                Mapped[str]   = mapped_column(String(16), nullable=False)
    # Snapshot of holdings + start prices at quote time
    portfolio_snapshot:  Mapped[dict]  = mapped_column(JSON, default=dict, nullable=False)
    portfolio_value_inr: Mapped[float] = mapped_column(Float, nullable=False)

    # Pricing outputs
    notional_inr:        Mapped[float] = mapped_column(Float, nullable=False)
    premium_inr:         Mapped[float] = mapped_column(Float, nullable=False)
    loss_threshold:      Mapped[float] = mapped_column(Float, nullable=False)
    profit_threshold:    Mapped[float] = mapped_column(Float, nullable=False)
    coverage_rate:       Mapped[float] = mapped_column(Float, nullable=False)
    profit_share_rate:   Mapped[float] = mapped_column(Float, nullable=False)
    max_payout_inr:      Mapped[float] = mapped_column(Float, nullable=False)
    expected_payout:     Mapped[float] = mapped_column(Float, nullable=False)
    risk_margin:         Mapped[float] = mapped_column(Float, nullable=False)
    capital_fee:         Mapped[float] = mapped_column(Float, nullable=False)

    # Underwriting
    eligible:            Mapped[bool]  = mapped_column(Boolean, nullable=False)
    eligibility_reasons: Mapped[list]  = mapped_column(JSON, default=list, nullable=False)
    rules_version:       Mapped[str]   = mapped_column(String(64), nullable=False, default="default-v1")

    # Status: QUOTED | CONVERTED | REJECTED
    status:              Mapped[str]   = mapped_column(String(16), default="QUOTED", nullable=False)
    created_at:          Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user         = relationship("User",        back_populates="quotes")
    org          = relationship("Org",         back_populates="quotes")
    portfolio    = relationship("Portfolio",   back_populates="quotes")
    ml_inference = relationship("MLInference", back_populates="quote")
    policy       = relationship("Policy",      back_populates="quote", uselist=False)
