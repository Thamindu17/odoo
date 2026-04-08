from __future__ import annotations

from datetime import date
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


FALLBACK_FIELD_PROMPTS = {
    "first_name": "May I know your name, please?",
    "last_name": "And your last name?",
    "title": "How should I address you? Please choose: Mr., Ms., Dr., Prof., or Rev.",
    "city": "Which city are you based in?",
    "requirement_summary": "How can we help you today? Please describe your requirement briefly.",
}

FALLBACK_FIELD_REASK = {
    "first_name": "Could you please provide your first name?",
    "last_name": "Could you please provide your last name?",
    "title": "Please choose: Mr., Ms., Dr., Prof., or Rev.",
    "city": "Could you please share your city name?",
    "requirement_summary": "Could you tell us a bit more about what you're looking for?",
}

FIELD_ORDER_NEW = ["first_name", "last_name", "title", "city", "requirement_summary"]
FIELD_ORDER_EXISTING = ["requirement_summary"]

ALLOWED_CATEGORY_LABELS = {
    "maternity": "Maternity",
    "wellness": "Wellness",
    "surgery": "Surgery",
    "cag": "CAG",
    "mri": "MRI",
}

# Fallback keywords used only when LLM does not provide a confident category.
CATEGORY_KEYWORDS = {
    "maternity": ["maternity", "pregnan", "delivery", "baby", "prenatal", "postnatal"],
    "wellness": ["wellness", "checkup", "check-up", "health package", "preventive"],
    "surgery": ["surgery", "operation", "surgical", "procedure"],
    "cag": ["cag", "angiogram", "coronary angiogram", "angiography"],
    "mri": ["mri", "scan", "magnetic resonance"],
}

TITLE_MAP = {
    "mr": "mr",
    "mr.": "mr",
    "mister": "mr",
    "ms": "ms",
    "ms.": "ms",
    "mrs": "ms",
    "mrs.": "ms",
    "miss": "ms",
    "dr": "dr",
    "dr.": "dr",
    "doctor": "dr",
    "prof": "prof",
    "prof.": "prof",
    "professor": "prof",
    "rev": "rev",
    "rev.": "rev",
    "reverend": "rev",
}

HUMAN_KEYWORDS = {
    "human",
    "agent",
    "representative",
    "person",
    "operator",
    "talk to someone",
    "connect me",
    "customer care",
}

NON_NAME_TOKENS = {
    "ok",
    "okay",
    "yes",
    "no",
    "hi",
    "hello",
    "hey",
    "sure",
    "fine",
    "thanks",
    "thank you",
    "k",
    "kk",
}

SHORT_SUMMARY_TOKENS = {
    "mri",
    "scan",
    "cag",
    "angiogram",
    "surgery",
    "operation",
    "wellness",
    "checkup",
    "check-up",
    "consultation",
    "pregnancy",
    "maternity",
    "delivery",
    "screening",
    "package",
}

DUMMY_VALUES = {
    "first_name": "Unknown",
    "last_name": "Pending",
    "title": "mr",
    "city": "Unknown",
    "requirement_summary": "Client disconnected before sharing full requirement; follow-up required.",
}


def _parse_iso_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _should_timeout(last_client_message_at: str | None, now_at: str | None) -> bool:
    last_seen = _parse_iso_datetime(last_client_message_at)
    if not last_seen:
        return False
    now_value = _parse_iso_datetime(now_at) or datetime.now(timezone.utc)
    return now_value - last_seen > timedelta(minutes=5)


def _normalize_title(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    return TITLE_MAP.get(key)


def _validate_alpha_spaces(value: str) -> bool:
    text = value.strip()
    if not text or len(text) > 100:
        return False
    return all(ch.isalpha() or ch.isspace() for ch in text)


def _looks_like_ack_name(value: str) -> bool:
    lowered = " ".join(value.strip().lower().split())
    return lowered in NON_NAME_TOKENS


def _validate_city(value: str) -> bool:
    text = value.strip()
    return bool(text and len(text) <= 100)


def _validate_summary(value: str) -> bool:
    normalized = " ".join(value.strip().lower().split())
    if not normalized:
        return False

    if normalized in NON_NAME_TOKENS or normalized.startswith("thank"):
        return False

    if len(normalized) >= 10:
        return True

    tokens = normalized.replace("/", " ").replace("-", " ").split()
    if any(token in SHORT_SUMMARY_TOKENS for token in tokens):
        return True

    for keywords in CATEGORY_KEYWORDS.values():
        if any(keyword in normalized for keyword in keywords):
            return True

    return False


def _validate_field(field_name: str, value: str) -> tuple[bool, str | None]:
    text = value.strip()
    if field_name in {"first_name", "last_name"}:
        if not _validate_alpha_spaces(text):
            return (False, text)
        if _looks_like_ack_name(text):
            return (False, text)
        return (True, text)
    if field_name == "title":
        normalized = _normalize_title(text)
        return (normalized is not None, normalized)
    if field_name == "city":
        return (_validate_city(text), text)
    if field_name == "requirement_summary":
        return (_validate_summary(text), text)
    return (False, None)


def _next_missing_field(order: list[str], collected: dict[str, Any]) -> str | None:
    for field in order:
        value = str(collected.get(field) or "").strip()
        if not value:
            return field
    return None


def _contains_human_request(message: str) -> bool:
    lower = message.strip().lower()
    return any(keyword in lower for keyword in HUMAN_KEYWORDS)


def _normalize_category_hint(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    if key in ALLOWED_CATEGORY_LABELS:
        return key
    for allowed_key, label in ALLOWED_CATEGORY_LABELS.items():
        if key == label.lower():
            return allowed_key
    return None


def _infer_category(
    summary: str,
    categories: list[dict[str, Any]],
    category_hint: str | None = None,
) -> tuple[int | None, str | None]:
    active_by_key: dict[str, dict[str, Any]] = {}
    for cat in categories:
        name = str(cat.get("name") or "").strip().lower()
        normalized = _normalize_category_hint(name)
        if normalized:
            active_by_key[normalized] = cat

    hinted_key = _normalize_category_hint(category_hint)
    if hinted_key and hinted_key in active_by_key:
        match = active_by_key[hinted_key]
        return int(match["id"]), str(match.get("name") or ALLOWED_CATEGORY_LABELS[hinted_key])

    text = summary.lower()
    matched_keys: list[str] = []
    for key, keywords in CATEGORY_KEYWORDS.items():
        if key not in active_by_key:
            continue
        if any(token in text for token in keywords):
            matched_keys.append(key)

    if len(matched_keys) == 1:
        match = active_by_key[matched_keys[0]]
        return int(match["id"]), str(match.get("name") or ALLOWED_CATEGORY_LABELS[matched_keys[0]])

    # Fallback exact label match in free text.
    exact_matches: list[str] = []
    for key, label in ALLOWED_CATEGORY_LABELS.items():
        if key not in active_by_key:
            continue
        if label.lower() in text:
            exact_matches.append(key)

    if len(exact_matches) == 1:
        match = active_by_key[exact_matches[0]]
        return int(match["id"]), str(match.get("name") or ALLOWED_CATEGORY_LABELS[exact_matches[0]])

    return None, None


def _dummy_nic_from_phone(normalized_phone: str) -> str:
    return f"99{normalized_phone}"


def _source_name_from_channel(channel_name: str) -> str:
    channel = channel_name.strip().lower()
    if channel in {
        "whatsapp",
        "facebook",
        "facebook messenger",
        "facebook_messenger",
        "messenger",
        "instagram",
        "social media",
        "social_media",
    }:
        return "Social Media"
    if channel in {"website", "website live chat", "website_live_chat", "web", "internal_test"}:
        return "Website"
    return "Other"


def _first_name_from_partner(partner: dict[str, Any]) -> str | None:
    first = str(partner.get("hp_first_name") or "").strip()
    if first:
        return first
    name = str(partner.get("name") or "").strip()
    if not name:
        return None
    return name.split()[0]


def _city_name_from_partner(partner: dict[str, Any]) -> str | None:
    raw = partner.get("hp_city_category")
    if isinstance(raw, (list, tuple)) and len(raw) >= 2:
        return str(raw[1] or "").strip() or None
    return None


def _lead_reference_text(lead: dict[str, Any]) -> str:
    lead_name = str(lead.get("name") or "").strip()
    lead_id = lead.get("id")
    if lead_name:
        return lead_name
    if lead_id is not None:
        return f"LEAD-{lead_id}"
    return "your enquiry"


def _build_lead_name(first_name: str, category_name: str | None) -> str:
    today = date.today().isoformat()
    first = first_name.strip() or "Client"
    category = (category_name or "General").strip() or "General"
    return f"{category} / {first} / {today}"


def _display_client_name(collected: dict[str, Any], partner: dict[str, Any] | None) -> str:
    first = str(collected.get("first_name") or "").strip()
    last = str(collected.get("last_name") or "").strip()
    joined = " ".join(part for part in [first, last] if part).strip()
    if joined:
        return joined

    partner_data = partner or {}
    partner_first = str(partner_data.get("hp_first_name") or "").strip()
    partner_last = str(partner_data.get("hp_last_name") or "").strip()
    partner_joined = " ".join(part for part in [partner_first, partner_last] if part).strip()
    if partner_joined:
        return partner_joined

    return str(partner_data.get("name") or "Client").strip() or "Client"


def _compose_reply(
    compose_reply: Callable[[str, str | None, dict[str, Any]], str],
    intent: str,
    field_name: str | None,
    collected: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> str:
    payload = {
        "first_name": str(collected.get("first_name") or "").strip() or None,
        "captured_field": (context or {}).get("captured_field"),
        "lead_reference": (context or {}).get("lead_reference"),
        "channel_name": (context or {}).get("channel_name"),
        "handover_reason": (context or {}).get("handover_reason"),
    }
    if context:
        payload.update(context)

    try:
        response = compose_reply(intent, field_name, payload)
        if isinstance(response, str) and response.strip():
            return response.strip()
    except Exception:
        pass

    first_name = str(collected.get("first_name") or "").strip()
    if intent == "ask_field":
        return FALLBACK_FIELD_PROMPTS.get(field_name or "", "Could you please share more details?")
    if intent == "retry_field":
        return FALLBACK_FIELD_REASK.get(field_name or "", "Could you please clarify that?")
    if intent == "ack_and_ask":
        next_prompt = FALLBACK_FIELD_PROMPTS.get(field_name or "", "Could you please share the next detail?")
        if first_name and payload.get("captured_field") == "first_name":
            return f"Thanks, {first_name}. {next_prompt}"
        return f"Thanks. {next_prompt}"
    if intent == "ready_to_create":
        return "Thank you. I have enough details to register your enquiry."
    if intent == "handover":
        return "I'm connecting you with a member of our team who can assist you further. Please hold."
    if intent == "missing_phone":
        return "I need a contact number before I can register your enquiry. I'm connecting you with our team."
    if intent == "completion":
        lead_reference = str(payload.get("lead_reference") or "").strip()
        if first_name and lead_reference:
            return f"Thank you, {first_name}! Your enquiry is registered. Reference: {lead_reference}. Our team will contact you shortly."
        return "Thank you. Your enquiry has been registered. Our team will contact you shortly."
    if intent == "partial_timeout":
        return "Your enquiry has been saved with available details. Our team will follow up shortly."
    return "Thank you. We will continue with your enquiry."


def process_requirement_turn(
    flow_type: str,
    channel_name: str,
    normalized_phone: str | None,
    partner_id: int | None,
    current_field: str | None,
    user_message: str | None,
    collected_data: dict[str, Any],
    retry_counts: dict[str, int],
    last_client_message_at: str | None,
    now_at: str | None,
    auto_create_on_completion: bool,
    extract_entities: Callable[[str], dict[str, Any]],
    classify_category: Callable[[str], str | None],
    summarize_requirement: Callable[[str], str | None],
    compose_reply: Callable[[str, str | None, dict[str, Any]], str],
    search_partners_by_phone: Callable[[str], list[dict[str, Any]]],
    count_active_leads_for_partner: Callable[[int], int],
    get_latest_active_lead: Callable[[int], dict[str, Any] | None],
    post_lead_chatter: Callable[[int, str], bool],
    get_partner: Callable[[int], dict[str, Any] | None],
    list_categories: Callable[[], list[dict[str, Any]]],
    resolve_hospital_city: Callable[[str], int],
    resolve_ruhunu_city: Callable[[str], int],
    resolve_lead_source: Callable[[str], dict[str, Any]],
    create_partner: Callable[[dict[str, Any]], int],
    create_lead: Callable[[dict[str, Any]], int],
    get_lead: Callable[[int], dict[str, Any] | None],
) -> dict[str, Any]:
    flow = flow_type.strip().lower()
    if flow not in {"new_client", "existing_no_active"}:
        return {
            "status": "handover",
            "next_step": "handover_agent",
            "bot_message": _compose_reply(
                compose_reply,
                "handover",
                current_field,
                collected_data,
                {"handover_reason": "invalid_flow_type", "channel_name": channel_name},
            ),
            "current_field": current_field,
            "collected_data": collected_data,
            "retry_counts": retry_counts,
            "handover_reason": "invalid_flow_type",
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": True,
        }

    collected = dict(collected_data or {})
    retries = dict(retry_counts or {})

    resolved_partner_id = partner_id
    partner_matches: list[dict[str, Any]] = []
    if normalized_phone:
        partner_matches = search_partners_by_phone(normalized_phone)

        if len(partner_matches) > 1:
            return {
                "status": "handover",
                "next_step": "handover_agent",
                "bot_message": _compose_reply(
                    compose_reply,
                    "handover",
                    current_field,
                    collected,
                    {"handover_reason": "multiple_contact_matches", "channel_name": channel_name},
                ),
                "current_field": current_field,
                "collected_data": collected,
                "retry_counts": retries,
                "handover_reason": "multiple_contact_matches",
                "created_partner_id": None,
                "created_lead_id": None,
                "created_lead_name": None,
                "inferred_category_id": None,
                "inferred_category_name": None,
                "end_conversation": True,
            }

        if len(partner_matches) == 1:
            match_id = int(partner_matches[0]["id"])
            resolved_partner_id = resolved_partner_id or match_id
            if flow == "new_client":
                flow = "existing_no_active"

    if flow == "existing_no_active" and not resolved_partner_id:
        flow = "new_client"

    order = FIELD_ORDER_NEW if flow == "new_client" else FIELD_ORDER_EXISTING

    partner = get_partner(resolved_partner_id) if (flow == "existing_no_active" and resolved_partner_id) else None
    if flow == "existing_no_active" and resolved_partner_id and not partner:
        return {
            "status": "handover",
            "next_step": "handover_agent",
            "bot_message": _compose_reply(
                compose_reply,
                "handover",
                current_field,
                collected,
                {"handover_reason": "invalid_partner", "channel_name": channel_name},
            ),
            "current_field": current_field,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": "invalid_partner",
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": True,
        }

    if flow == "existing_no_active" and resolved_partner_id:
        active_count = max(0, int(count_active_leads_for_partner(int(resolved_partner_id)) or 0))
        if active_count > 0:
            latest_active = get_latest_active_lead(int(resolved_partner_id))
            if latest_active:
                lead_id = int(latest_active["id"])
                client_name = _display_client_name(collected, partner)
                chatter_note = (
                    f"Client {client_name} reached out via {channel_name} while having "
                    f"{active_count} active enquiry record(s). Please review and continue the conversation."
                )
                try:
                    post_lead_chatter(lead_id, chatter_note)
                except Exception:
                    pass

            reason = "multiple_active_leads" if active_count > 1 else "active_lead_exists"
            return {
                "status": "handover",
                "next_step": "notify_agent_and_end",
                "bot_message": _compose_reply(
                    compose_reply,
                    "handover",
                    current_field,
                    collected,
                    {"handover_reason": reason, "channel_name": channel_name},
                ),
                "current_field": current_field,
                "collected_data": collected,
                "retry_counts": retries,
                "handover_reason": reason,
                "created_partner_id": None,
                "created_lead_id": None,
                "created_lead_name": None,
                "inferred_category_id": None,
                "inferred_category_name": None,
                "end_conversation": True,
            }

    if partner:
        if not collected.get("first_name"):
            collected["first_name"] = _first_name_from_partner(partner)
        if not collected.get("last_name"):
            collected["last_name"] = str(partner.get("hp_last_name") or "").strip() or None
        if not collected.get("title"):
            collected["title"] = _normalize_title(str(partner.get("hp_salutation") or ""))
        if not collected.get("city"):
            collected["city"] = _city_name_from_partner(partner)

    if _should_timeout(last_client_message_at, now_at):
        min_first_name = bool(str(collected.get("first_name") or "").strip())
        min_phone = bool(str(normalized_phone or "").strip())
        if min_first_name and min_phone:
            completion = _complete_and_create(
                flow=flow,
                channel_name=channel_name,
                normalized_phone=normalized_phone,
                partner_id=resolved_partner_id,
                collected=collected,
                list_categories=list_categories,
                resolve_hospital_city=resolve_hospital_city,
                resolve_ruhunu_city=resolve_ruhunu_city,
                resolve_lead_source=resolve_lead_source,
                create_partner=create_partner,
                create_lead=create_lead,
                get_lead=get_lead,
                classify_category=classify_category,
                summarize_requirement=summarize_requirement,
                compose_reply=compose_reply,
                force_partial_summary=True,
            )
            completion["status"] = "partial_lead_created"
            completion["next_step"] = "end"
            completion["handover_reason"] = "timeout_partial_created"
            completion["bot_message"] = _compose_reply(
                compose_reply,
                "partial_timeout",
                None,
                completion.get("collected_data") or collected,
                {"channel_name": channel_name, "lead_reference": completion.get("created_lead_name")},
            )
            completion["end_conversation"] = True
            return completion

        return {
            "status": "handover",
            "next_step": "handover_agent",
            "bot_message": _compose_reply(
                compose_reply,
                "handover",
                current_field,
                collected,
                {"handover_reason": "timeout_insufficient_data", "channel_name": channel_name},
            ),
            "current_field": current_field,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": "timeout_insufficient_data",
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": True,
        }

    if not user_message or not user_message.strip():
        target = current_field or _next_missing_field(order, collected)
        if not target:
            if auto_create_on_completion:
                completion = _complete_and_create(
                    flow=flow,
                    channel_name=channel_name,
                    normalized_phone=normalized_phone,
                    partner_id=resolved_partner_id,
                    collected=collected,
                    list_categories=list_categories,
                    resolve_hospital_city=resolve_hospital_city,
                    resolve_ruhunu_city=resolve_ruhunu_city,
                    resolve_lead_source=resolve_lead_source,
                    create_partner=create_partner,
                    create_lead=create_lead,
                    get_lead=get_lead,
                    classify_category=classify_category,
                    summarize_requirement=summarize_requirement,
                    compose_reply=compose_reply,
                    force_partial_summary=False,
                )
                completion["status"] = "completed_created"
                completion["next_step"] = "end"
                completion["end_conversation"] = True
                return completion

            return {
                "status": "ready_to_create",
                "next_step": "create_records",
                "bot_message": _compose_reply(
                    compose_reply,
                    "ready_to_create",
                    None,
                    collected,
                    {"channel_name": channel_name},
                ),
                "current_field": None,
                "collected_data": collected,
                "retry_counts": retries,
                "handover_reason": None,
                "created_partner_id": None,
                "created_lead_id": None,
                "created_lead_name": None,
                "inferred_category_id": None,
                "inferred_category_name": None,
                "end_conversation": False,
            }

        return {
            "status": "ask_next",
            "next_step": "collect_data",
            "bot_message": _compose_reply(
                compose_reply,
                "ask_field",
                target,
                collected,
                {"channel_name": channel_name},
            ),
            "current_field": target,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": None,
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": False,
        }

    message = user_message.strip()
    extracted = extract_entities(message) or {}
    if _contains_human_request(message) or bool(extracted.get("human_request")):
        return {
            "status": "handover",
            "next_step": "handover_agent",
            "bot_message": _compose_reply(
                compose_reply,
                "handover",
                current_field,
                collected,
                {"handover_reason": "human_requested", "channel_name": channel_name},
            ),
            "current_field": current_field,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": "human_requested",
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": True,
        }

    target = current_field or _next_missing_field(order, collected) or order[-1]

    # Capture volunteered data without forcing re-ask.
    for field_name in ["first_name", "last_name", "title", "city", "requirement_summary"]:
        candidate = str(extracted.get(field_name) or "").strip()
        if not candidate:
            continue
        is_valid, normalized = _validate_field(field_name, candidate)
        if is_valid and normalized and not collected.get(field_name):
            collected[field_name] = normalized

    category_hint = str(extracted.get("lead_category_suggestion") or "").strip()
    if category_hint:
        normalized_hint = _normalize_category_hint(category_hint)
        if normalized_hint:
            collected["_lead_category_hint"] = ALLOWED_CATEGORY_LABELS[normalized_hint]

    if not collected.get("_lead_category_hint"):
        llm_category = classify_category(message)
        normalized_llm = _normalize_category_hint(llm_category)
        if normalized_llm:
            collected["_lead_category_hint"] = ALLOWED_CATEGORY_LABELS[normalized_llm]

    extracted_value = str(extracted.get(target) or "").strip()
    candidate_value = extracted_value or message
    is_valid, normalized_value = _validate_field(target, candidate_value)
    if not is_valid:
        # LLM extraction can be too short or imprecise; retry with raw user text before counting a failed attempt.
        raw_valid, raw_normalized = _validate_field(target, message)
        if raw_valid:
            candidate_value = message
            is_valid, normalized_value = raw_valid, raw_normalized
    if not is_valid or not normalized_value:
        attempts = int(retries.get(target, 0)) + 1
        retries[target] = attempts
        if attempts >= 2:
            return {
                "status": "handover",
                "next_step": "handover_agent",
                "bot_message": "I'm connecting you with a member of our team who can assist you further. Please hold.",
                "current_field": target,
                "collected_data": collected,
                "retry_counts": retries,
                "handover_reason": f"invalid_{target}",
                "created_partner_id": None,
                "created_lead_id": None,
                "created_lead_name": None,
                "inferred_category_id": None,
                "inferred_category_name": None,
                "end_conversation": True,
            }

        return {
            "status": "retry",
            "next_step": "collect_data",
            "bot_message": _compose_reply(
                compose_reply,
                "retry_field",
                target,
                collected,
                {"channel_name": channel_name},
            ),
            "current_field": target,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": None,
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": False,
        }

    collected[target] = normalized_value
    retries[target] = 0

    next_field = _next_missing_field(order, collected)
    if next_field:
        bot_message = _compose_reply(
            compose_reply,
            "ack_and_ask",
            next_field,
            collected,
            {"captured_field": target, "channel_name": channel_name},
        )
        return {
            "status": "ask_next",
            "next_step": "collect_data",
            "bot_message": bot_message,
            "current_field": next_field,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": None,
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": False,
        }

    if not auto_create_on_completion:
        category_id, category_name = _infer_category(
            str(collected.get("requirement_summary") or ""),
            list_categories(),
            str(collected.get("_lead_category_hint") or ""),
        )
        return {
            "status": "ready_to_create",
            "next_step": "create_records",
            "bot_message": _compose_reply(
                compose_reply,
                "ready_to_create",
                None,
                collected,
                {"channel_name": channel_name},
            ),
            "current_field": None,
            "collected_data": collected,
            "retry_counts": retries,
            "handover_reason": None,
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": category_id,
            "inferred_category_name": category_name,
            "end_conversation": False,
        }

    completion = _complete_and_create(
        flow=flow,
        channel_name=channel_name,
        normalized_phone=normalized_phone,
        partner_id=resolved_partner_id,
        collected=collected,
        list_categories=list_categories,
        resolve_hospital_city=resolve_hospital_city,
        resolve_ruhunu_city=resolve_ruhunu_city,
        resolve_lead_source=resolve_lead_source,
        create_partner=create_partner,
        create_lead=create_lead,
        get_lead=get_lead,
        classify_category=classify_category,
        summarize_requirement=summarize_requirement,
        compose_reply=compose_reply,
        force_partial_summary=False,
    )
    completion["status"] = "completed_created"
    completion["next_step"] = "end"
    completion["end_conversation"] = True
    return completion


def _complete_and_create(
    flow: str,
    channel_name: str,
    normalized_phone: str | None,
    partner_id: int | None,
    collected: dict[str, Any],
    list_categories: Callable[[], list[dict[str, Any]]],
    resolve_hospital_city: Callable[[str], int],
    resolve_ruhunu_city: Callable[[str], int],
    resolve_lead_source: Callable[[str], dict[str, Any]],
    create_partner: Callable[[dict[str, Any]], int],
    create_lead: Callable[[dict[str, Any]], int],
    get_lead: Callable[[int], dict[str, Any] | None],
    classify_category: Callable[[str], str | None],
    summarize_requirement: Callable[[str], str | None],
    compose_reply: Callable[[str, str | None, dict[str, Any]], str],
    force_partial_summary: bool,
) -> dict[str, Any]:
    if not normalized_phone:
        return {
            "status": "handover",
            "next_step": "handover_agent",
            "bot_message": _compose_reply(
                compose_reply,
                "missing_phone",
                None,
                collected,
                {"handover_reason": "missing_phone", "channel_name": channel_name},
            ),
            "current_field": None,
            "collected_data": collected,
            "retry_counts": {},
            "handover_reason": "missing_phone",
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": None,
            "inferred_category_name": None,
            "end_conversation": True,
        }

    safe = dict(collected)
    for key, default in DUMMY_VALUES.items():
        if not str(safe.get(key) or "").strip():
            safe[key] = default

    if force_partial_summary:
        safe["requirement_summary"] = DUMMY_VALUES["requirement_summary"]

    raw_requirement = str(safe.get("requirement_summary") or "").strip()

    if not safe.get("_lead_category_hint"):
        llm_category = classify_category(raw_requirement)
        normalized_llm = _normalize_category_hint(llm_category)
        if normalized_llm:
            safe["_lead_category_hint"] = ALLOWED_CATEGORY_LABELS[normalized_llm]

    if raw_requirement:
        english_summary = summarize_requirement(raw_requirement)
        if english_summary:
            safe["requirement_summary"] = english_summary

    category_id, category_name = _infer_category(
        str(safe.get("requirement_summary") or ""),
        list_categories(),
        str(safe.get("_lead_category_hint") or ""),
    )

    created_partner_id = partner_id
    if flow == "new_client":
        hospital_city_id = resolve_hospital_city(str(safe["city"]))
        created_partner_id = create_partner(
            {
                "company_type": "person",
                "hp_first_name": safe["first_name"],
                "hp_last_name": safe["last_name"],
                "hp_salutation": safe["title"],
                "phone": normalized_phone,
                "hp_whatsapp": normalized_phone,
                "hp_nic": _dummy_nic_from_phone(normalized_phone),
                "hp_birthday": "1990-01-01",
                "hp_city_category": hospital_city_id,
            }
        )

    if not created_partner_id:
        return {
            "status": "handover",
            "next_step": "handover_agent",
            "bot_message": _compose_reply(
                compose_reply,
                "handover",
                None,
                safe,
                {"handover_reason": "missing_partner", "channel_name": channel_name},
            ),
            "current_field": None,
            "collected_data": safe,
            "retry_counts": {},
            "handover_reason": "missing_partner",
            "created_partner_id": None,
            "created_lead_id": None,
            "created_lead_name": None,
            "inferred_category_id": category_id,
            "inferred_category_name": category_name,
            "end_conversation": True,
        }

    lead_city_id = resolve_ruhunu_city(str(safe["city"]))
    source_name = _source_name_from_channel(channel_name)
    lead_source = resolve_lead_source(source_name)
    lead_source_id = int(lead_source["id"]) if lead_source else None

    lead_vals = {
        "name": _build_lead_name(str(safe["first_name"]), category_name),
        "type": "opportunity",
        "partner_id": int(created_partner_id),
        "ruhunu_first_name": safe["first_name"],
        "ruhunu_last_name": safe["last_name"],
        "ruhunu_client_title": safe["title"],
        "ruhunu_contact_no": normalized_phone,
        "ruhunu_whatsapp_no": normalized_phone,
        "ruhunu_city_id": lead_city_id,
        "ruhunu_lead_summary": safe["requirement_summary"],
        "ruhunu_lead_source_id": lead_source_id,
    }
    if category_id:
        lead_vals["ruhunu_lead_category_id"] = int(category_id)

    lead_id = create_lead(lead_vals)
    lead = get_lead(lead_id) or {"id": lead_id}
    lead_ref = _lead_reference_text(lead)

    return {
        "status": "completed_created",
        "next_step": "end",
        "bot_message": _compose_reply(
            compose_reply,
            "completion",
            None,
            safe,
            {
                "lead_reference": lead_ref,
                "channel_name": channel_name,
            },
        ),
        "current_field": None,
        "collected_data": safe,
        "retry_counts": {},
        "handover_reason": None,
        "created_partner_id": int(created_partner_id),
        "created_lead_id": int(lead_id),
        "created_lead_name": str(lead.get("name") or ""),
        "inferred_category_id": category_id,
        "inferred_category_name": category_name,
        "end_conversation": True,
    }