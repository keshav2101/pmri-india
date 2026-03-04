"""services/audit_service.py — Immutable audit log service for quoting and admin actions."""
from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.policy import AuditLog

logger = logging.getLogger(__name__)

class AuditService:
    @staticmethod
    def log_event(db: AsyncSession, event_type: str, payload_json: dict, user_id: str = None, entity_id: str = None):
        """Write an immutable audit record."""
        try:
            log = AuditLog(
                event_type=event_type,
                user_id=user_id,
                entity_id=entity_id,
                payload_json=payload_json
            )
            db.add(log)
        except Exception as e:
            logger.error("Failed to write audit log: %s", e, exc_info=True)


audit_service = AuditService()
