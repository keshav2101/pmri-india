"""schemas/org.py — Org and OrgMember schemas for PMRI India."""
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class OrgCreate(BaseModel):
    name: str
    tier: str = "INSTITUTIONAL_BASIC"

class AddMemberRequest(BaseModel):
    email: str
    role: str = "MEMBER"   # OWNER | MEMBER

class OrgMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    role: str
    joined_at: datetime

class OrgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tier: str
    created_at: datetime
    members: List[OrgMemberResponse] = []
