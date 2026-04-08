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


class ClientIdentificationRequest(BaseModel):
    channel_name: str = Field(default="internal_test", min_length=1)
    metadata_phone: str | None = None
    provided_phone: str | None = None
    invalid_phone_attempts: int = Field(default=0, ge=0, le=5)


class ClientIdentificationResponse(BaseModel):
    status: str
    next_step: str
    message: str
    invalid_phone_attempts: int
    normalized_phone: str | None = None
    partner_count: int
    partner: dict[str, Any] | None = None
    matched_partners: list[dict[str, Any]] = Field(default_factory=list)


class ActiveLeadCheckRequest(BaseModel):
    partner_id: int = Field(ge=1)
    channel_name: str = Field(default="internal_test", min_length=1)


class ActiveLeadCheckResponse(BaseModel):
    status: str
    next_step: str
    client_message: str
    has_active_lead: bool
    lead: dict[str, Any] | None = None
    agent_name: str | None = None
    notification_posted: bool = False
    end_conversation: bool = False


class RequirementGatheringRequest(BaseModel):
    flow_type: str = Field(description="new_client or existing_no_active")
    channel_name: str = Field(default="internal_test", min_length=1)
    normalized_phone: str | None = None
    partner_id: int | None = None

    current_field: str | None = None
    user_message: str | None = None
    collected_data: dict[str, Any] = Field(default_factory=dict)
    retry_counts: dict[str, int] = Field(default_factory=dict)

    last_client_message_at: str | None = None
    now_at: str | None = None
    auto_create_on_completion: bool = True


class RequirementGatheringResponse(BaseModel):
    status: str
    next_step: str
    bot_message: str

    current_field: str | None = None
    collected_data: dict[str, Any] = Field(default_factory=dict)
    retry_counts: dict[str, int] = Field(default_factory=dict)

    handover_reason: str | None = None
    created_partner_id: int | None = None
    created_lead_id: int | None = None
    created_lead_name: str | None = None
    inferred_category_id: int | None = None
    inferred_category_name: str | None = None
    end_conversation: bool = False
