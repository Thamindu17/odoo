from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .config import get_settings
from .gemini_client import GeminiClient
from .odoo_client import OdooClient
from .schemas import (
    ActionEnvelope,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    LeadArchiveRequest,
    LeadCreateRequest,
    LeadListRequest,
    LeadResult,
    LeadUpdateRequest,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)
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
        req = LeadUpdateRequest(**payload)
        result = update_lead(req)
        return ChatResponse(
            action=name,
            details=result,
            response=f"Lead #{req.lead_id} updated.",
        )

    if name == "archive_lead":
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
