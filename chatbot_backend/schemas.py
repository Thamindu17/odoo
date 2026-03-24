from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str
    env: str


class LeadCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    email_from: str | None = None
    phone: str | None = None
    priority: str | None = None
    expected_revenue: float | None = None
    partner_id: int | None = None
    user_id: int | None = None
    stage_id: int | None = None


class LeadUpdateRequest(BaseModel):
    lead_id: int
    name: str | None = None
    description: str | None = None
    email_from: str | None = None
    phone: str | None = None
    priority: str | None = None
    expected_revenue: float | None = None
    partner_id: int | None = None
    user_id: int | None = None
    stage_id: int | None = None


class LeadArchiveRequest(BaseModel):
    lead_id: int


class LeadListRequest(BaseModel):
    name_contains: str | None = None
    stage_id: int | None = None
    priority: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class LeadResult(BaseModel):
    id: int
    name: str
    stage_id: Any = None
    priority: str | None = None
    email_from: str | None = None
    phone: str | None = None
    expected_revenue: float | None = None
    active: bool | None = None


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    action: str
    details: dict[str, Any]
    response: str


class ActionEnvelope(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
