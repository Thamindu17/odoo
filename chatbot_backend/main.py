from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .active_lead_routing import check_existing_client_active_lead
from .client_identification import identify_client
from .config import get_settings
from .gemini_client import GeminiClient
from .odoo_client import OdooClient
from .requirement_gathering import process_requirement_turn
from .schemas import (
    ActiveLeadCheckRequest,
    ActiveLeadCheckResponse,
    ActionEnvelope,
    ChatRequest,
    ChatResponse,
    ClientIdentificationRequest,
    ClientIdentificationResponse,
    HealthResponse,
    LeadArchiveRequest,
    LeadCreateRequest,
    LeadListRequest,
    LeadResult,
    LeadUpdateRequest,
    RequirementGatheringRequest,
    RequirementGatheringResponse,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8888",
        "http://localhost:8888",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
odoo_client = OdooClient(settings)
gemini_client = GeminiClient(settings)


ALLOWED_UPDATE_FIELDS = {
    "name",
    "description",
    "email_from",
    "phone",
    "priority",
    "expected_revenue",
    "partner_id",
    "user_id",
    "stage_id",
}


def _lead_fields() -> list[str]:
    return [
        "id",
        "name",
        "stage_id",
        "priority",
        "email_from",
        "phone",
        "expected_revenue",
        "active",
    ]


def _build_domain(payload: LeadListRequest) -> list[list]:
    domain: list[list] = []
    if payload.name_contains:
        domain.append(["name", "ilike", payload.name_contains])
    if payload.stage_id is not None:
        domain.append(["stage_id", "=", payload.stage_id])
    if payload.priority is not None:
        domain.append(["priority", "=", payload.priority])
    return domain


def _resolve_lead_id(lead_name: str) -> int:
    leads = odoo_client.list_leads([["name", "ilike", lead_name], ["active", "=", True]], ["id", "name"], 1)
    if not leads:
        raise HTTPException(status_code=404, detail=f"Lead not found by name: {lead_name}")
    return int(leads[0]["id"])


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, env=settings.app_env)


@app.post("/crm/create", response_model=LeadResult)
def create_lead(req: LeadCreateRequest) -> LeadResult:
    vals = req.model_dump(exclude_none=True)
    try:
        lead_id = odoo_client.create_lead(vals)
        leads = odoo_client.list_leads([["id", "=", lead_id]], _lead_fields(), 1)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not leads:
        raise HTTPException(status_code=404, detail="Lead created but not found")
    return LeadResult(**leads[0])


@app.post("/crm/list", response_model=list[LeadResult])
def list_leads(req: LeadListRequest) -> list[LeadResult]:
    domain = _build_domain(req)
    try:
        records = odoo_client.list_leads(domain, _lead_fields(), req.limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [LeadResult(**row) for row in records]


@app.post("/crm/update", response_model=dict)
def update_lead(req: LeadUpdateRequest) -> dict:
    vals = {k: v for k, v in req.model_dump(exclude_none=True).items() if k in ALLOWED_UPDATE_FIELDS}
    if not vals:
        raise HTTPException(status_code=400, detail="No update fields provided")

    try:
        ok = odoo_client.update_lead(req.lead_id, vals)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"updated": bool(ok), "lead_id": req.lead_id, "fields": list(vals.keys())}


@app.post("/crm/archive", response_model=dict)
def archive_lead(req: LeadArchiveRequest) -> dict:
    try:
        ok = odoo_client.archive_lead(req.lead_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"archived": bool(ok), "lead_id": req.lead_id}


@app.post("/qualification/identify", response_model=ClientIdentificationResponse)
def qualification_identify(req: ClientIdentificationRequest) -> ClientIdentificationResponse:
    try:
        result = identify_client(
            metadata_phone=req.metadata_phone,
            provided_phone=req.provided_phone,
            invalid_phone_attempts=req.invalid_phone_attempts,
            search_partners_by_phone=odoo_client.search_individual_partners_by_phone,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ClientIdentificationResponse(**result)


@app.post("/qualification/active-lead-check", response_model=ActiveLeadCheckResponse)
def qualification_active_lead_check(req: ActiveLeadCheckRequest) -> ActiveLeadCheckResponse:
    try:
        result = check_existing_client_active_lead(
            partner_id=req.partner_id,
            channel_name=req.channel_name,
            get_partner=odoo_client.get_partner_profile,
            get_latest_active_lead=odoo_client.get_latest_active_lead_for_partner,
            post_lead_chatter=odoo_client.post_lead_chatter_note,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ActiveLeadCheckResponse(**result)


@app.post("/qualification/requirement-gathering", response_model=RequirementGatheringResponse)
def qualification_requirement_gathering(req: RequirementGatheringRequest) -> RequirementGatheringResponse:
    try:
        result = process_requirement_turn(
            flow_type=req.flow_type,
            channel_name=req.channel_name,
            normalized_phone=req.normalized_phone,
            partner_id=req.partner_id,
            current_field=req.current_field,
            user_message=req.user_message,
            collected_data=req.collected_data,
            retry_counts=req.retry_counts,
            last_client_message_at=req.last_client_message_at,
            now_at=req.now_at,
            auto_create_on_completion=req.auto_create_on_completion,
            extract_entities=gemini_client.extract_requirement_entities,
            classify_category=gemini_client.classify_requirement_category,
            summarize_requirement=gemini_client.summarize_requirement_english,
            compose_reply=gemini_client.compose_requirement_reply,
            search_partners_by_phone=odoo_client.search_individual_partners_by_phone,
            count_active_leads_for_partner=odoo_client.count_active_leads_for_partner,
            get_latest_active_lead=odoo_client.get_latest_active_lead_for_partner,
            post_lead_chatter=odoo_client.post_lead_chatter_note,
            get_partner=odoo_client.get_partner_profile,
            list_categories=odoo_client.list_active_lead_categories,
            resolve_hospital_city=odoo_client.resolve_or_create_hospital_city,
            resolve_ruhunu_city=odoo_client.resolve_or_create_ruhunu_city,
            resolve_lead_source=odoo_client.resolve_or_create_lead_source,
            create_partner=odoo_client.create_partner,
            create_lead=odoo_client.create_lead,
            get_lead=odoo_client.get_lead_by_id,
        )
    except Exception as exc:
        detail = str(exc).strip() or repr(exc)
        raise HTTPException(status_code=400, detail=detail) from exc

    return RequirementGatheringResponse(**result)


def _execute_action(action: ActionEnvelope) -> ChatResponse:
    name = action.action
    payload = action.payload

    if name == "create_lead":
        req = LeadCreateRequest(**payload)
        result = create_lead(req)
        return ChatResponse(
            action=name,
            details=result.model_dump(),
            response=f"Lead created: #{result.id} {result.name}",
        )

    if name == "list_leads":
        req = LeadListRequest(**payload)
        rows = list_leads(req)
        return ChatResponse(
            action=name,
            details={"count": len(rows), "records": [r.model_dump() for r in rows]},
            response=f"Found {len(rows)} lead(s).",
        )

    if name == "update_lead":
        if "lead_id" not in payload:
            lead_name = payload.get("lead_name") or payload.get("name_contains")
            if lead_name:
                payload = dict(payload)
                payload["lead_id"] = _resolve_lead_id(str(lead_name))
                payload.pop("lead_name", None)

        req = LeadUpdateRequest(**payload)
        result = update_lead(req)
        return ChatResponse(
            action=name,
            details=result,
            response=f"Lead #{req.lead_id} updated.",
        )

    if name == "archive_lead":
        if "lead_id" not in payload:
            lead_name = payload.get("lead_name") or payload.get("name") or payload.get("name_contains")
            if lead_name:
                payload = dict(payload)
                payload["lead_id"] = _resolve_lead_id(str(lead_name))
                payload.pop("lead_name", None)

        req = LeadArchiveRequest(**payload)
        result = archive_lead(req)
        return ChatResponse(
            action=name,
            details=result,
            response=f"Lead #{req.lead_id} archived.",
        )

    return ChatResponse(
        action="unknown",
        details={"payload": payload},
        response=(
            "I could not map that request to a CRM action. "
            "Try phrases like: create lead, list leads, update lead, archive lead."
        ),
    )


@app.post("/chat/message", response_model=ChatResponse)
def chat_message(req: ChatRequest) -> ChatResponse:
    try:
        inferred = gemini_client.infer_action(req.message)
        action = ActionEnvelope(**inferred)
        return _execute_action(action)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
