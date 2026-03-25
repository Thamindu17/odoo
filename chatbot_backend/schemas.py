from typing import Any

from pydantic import BaseModel, Field, field_validator


def _normalize_priority(value: Any) -> str | None:
    if value in (None, False, "", "null"):
        return None

    if isinstance(value, int):
        value = str(value)

    if isinstance(value, str):
        value = value.strip()
        if value in {"0", "1", "2", "3"}:
            return value

    raise ValueError("priority must be one of 0, 1, 2, 3")


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

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, value: Any) -> str | None:
        return _normalize_priority(value)


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

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, value: Any) -> str | None:
        return _normalize_priority(value)


class LeadArchiveRequest(BaseModel):
    lead_id: int


class LeadListRequest(BaseModel):
    name_contains: str | None = None
    stage_id: int | None = None
    priority: str | None = None
    limit: int = Field(default=10, ge=1, le=100)

    @field_validator("priority", mode="before")
    @classmethod
    def _coerce_priority(cls, value: Any) -> str | None:
        return _normalize_priority(value)


class LeadResult(BaseModel):
    id: int
    name: str
    stage_id: Any = None
    priority: str | None = None
    email_from: str | None = None
    phone: str | None = None
    expected_revenue: float | None = None
    active: bool | None = None

    @field_validator("email_from", "phone", mode="before")
    @classmethod
    def _coerce_false_to_none(cls, value: Any) -> Any:
        if value is False:
            return None
        return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    action: str
    details: dict[str, Any]
    response: str


class ActionEnvelope(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
