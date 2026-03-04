"""models/policy.py — Policy, Settlement, LedgerTransaction, RulesConfig, AuditLog ORM models."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, JSON, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id:                    Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id:              Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=False, unique=True)
    user_id:               Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    org_id:                Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.id"), nullable=True)
    portfolio_id:          Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False)

    term:                  Mapped[str]   = mapped_column(String(16), nullable=False)
    notional_inr:          Mapped[float] = mapped_column(Float, nullable=False)
    premium_inr:           Mapped[float] = mapped_column(Float, nullable=False)
    loss_threshold:        Mapped[float] = mapped_column(Float, nullable=False)
    profit_threshold:      Mapped[float] = mapped_column(Float, nullable=False)
    coverage_rate:         Mapped[float] = mapped_column(Float, nullable=False)
    profit_share_rate:     Mapped[float] = mapped_column(Float, nullable=False)
    max_payout_inr:        Mapped[float] = mapped_column(Float, nullable=False)

    # Snapshot of portfolio value at policy start (from quote)
    start_portfolio_value: Mapped[float] = mapped_column(Float, nullable=False)
    portfolio_snapshot:    Mapped[dict]  = mapped_column(JSON, default=dict, nullable=False)

    start_date:  Mapped[datetime]          = mapped_column(DateTime(timezone=True), nullable=False)
    end_date:    Mapped[datetime]          = mapped_column(DateTime(timezone=True), nullable=False)
    # ACTIVE | MATURED | SETTLED
    status:      Mapped[str]               = mapped_column(String(16), default="ACTIVE", nullable=False)
    created_at:  Mapped[datetime]          = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user       = relationship("User",      back_populates="policies")
    org        = relationship("Org",       back_populates="policies")
    quote      = relationship("Quote",     back_populates="policy")
    settlement = relationship("Settlement", back_populates="policy", uselist=False)
    ledger_transactions = relationship("LedgerTransaction", back_populates="policy", cascade="all, delete-orphan")


class Settlement(Base):
    __tablename__ = "settlements"

    id:                   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id:            Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False, unique=True)
    # End portfolio value (from market prices at maturity)
    end_portfolio_value:  Mapped[float]     = mapped_column(Float, nullable=False)
    portfolio_return_pct: Mapped[float]     = mapped_column(Float, nullable=False)
    payout_inr:           Mapped[float]     = mapped_column(Float, nullable=False, default=0.0)
    surplus_inr:          Mapped[float]     = mapped_column(Float, nullable=False, default=0.0)
    # PROTECTION_TRIGGERED | PROFIT_SHARE | NO_ACTION
    outcome:              Mapped[str]       = mapped_column(String(32), nullable=False)
    settled_at:           Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    policy = relationship("Policy", back_populates="settlement")


class LedgerTransaction(Base):
    __tablename__ = "ledger_transactions"

    id:          Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id:   Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("policies.id"), nullable=False)
    tx_type:     Mapped[str]       = mapped_column(String(32), nullable=False)   # PREMIUM_PAID | PAYOUT | SURPLUS_SHARE
    amount_inr:  Mapped[float]     = mapped_column(Float, nullable=False)         # negative = debit
    description: Mapped[str]       = mapped_column(Text, nullable=False, default="")
    created_at:  Mapped[datetime]  = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    policy = relationship("Policy", back_populates="ledger_transactions")


class RulesConfig(Base):
    """Tier-based underwriting configuration — admin-updatable via /rules."""
    __tablename__ = "rules_config"

    id:             Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # RETAIL | INSTITUTIONAL_BASIC | INSTITUTIONAL_PREMIUM
    tier:           Mapped[str]               = mapped_column(String(32), unique=True, nullable=False)
    config_json:    Mapped[dict]              = mapped_column(JSON, nullable=False)
    updated_at:     Mapped[datetime]          = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by:     Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)


class AuditLog(Base):
    """Immutable audit trail for quote decisions and admin actions."""
    __tablename__ = "audit_log"

    id:           Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type:   Mapped[str]       = mapped_column(String(64), nullable=False, index=True)
    user_id:      Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    entity_id:    Mapped[Optional[str]]       = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict]       = mapped_column(JSON, default=dict, nullable=False)
    created_at:   Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
