from __future__ import annotations

import re
from typing import Any, Callable


_PHONE_PATTERN = re.compile(r"^0\d{9}$")


def normalize_phone(raw_phone: str) -> str | None:
    if not raw_phone:
        return None

    cleaned = re.sub(r"[\s\-()]+", "", raw_phone.strip())
    digits = re.sub(r"\D", "", cleaned)

    if digits.startswith("94") and len(digits) == 11:
        digits = f"0{digits[2:]}"

    if _PHONE_PATTERN.match(digits):
        return digits
    return None


def identify_client(
    metadata_phone: str | None,
    provided_phone: str | None,
    invalid_phone_attempts: int,
    search_partners_by_phone: Callable[[str], list[dict[str, Any]]],
) -> dict[str, Any]:
    candidate_phone = metadata_phone or provided_phone
    is_client_input = bool(provided_phone and not metadata_phone)

    if not candidate_phone:
        return {
            "status": "need_phone",
            "next_step": "ask_phone",
            "message": "Welcome to Ruhunu Hospital! To assist you better, could you please share your contact number?",
            "invalid_phone_attempts": invalid_phone_attempts,
            "normalized_phone": None,
            "partner_count": 0,
            "partner": None,
            "matched_partners": [],
        }

    normalized_phone = normalize_phone(candidate_phone)
    if not normalized_phone:
        if not is_client_input:
            return {
                "status": "need_phone",
                "next_step": "ask_phone",
                "message": "Welcome to Ruhunu Hospital! To assist you better, could you please share your contact number?",
                "invalid_phone_attempts": invalid_phone_attempts,
                "normalized_phone": None,
                "partner_count": 0,
                "partner": None,
                "matched_partners": [],
            }

        next_attempts = invalid_phone_attempts + 1
        if next_attempts >= 2:
            return {
                "status": "handover_invalid_phone",
                "next_step": "handover_agent",
                "message": "I'm connecting you with a member of our team who can assist you further. Please hold.",
                "invalid_phone_attempts": next_attempts,
                "normalized_phone": None,
                "partner_count": 0,
                "partner": None,
                "matched_partners": [],
            }

        return {
            "status": "need_phone",
            "next_step": "ask_phone",
            "message": "That number format looks invalid. Please share a valid contact number like 07XXXXXXXX.",
            "invalid_phone_attempts": next_attempts,
            "normalized_phone": None,
            "partner_count": 0,
            "partner": None,
            "matched_partners": [],
        }

    partners = search_partners_by_phone(normalized_phone)
    partner_count = len(partners)

    if partner_count == 0:
        return {
            "status": "new_client",
            "next_step": "requirement_gathering_new",
            "message": "Thank you. I could not find an existing profile, so I will register your enquiry as a new client.",
            "invalid_phone_attempts": invalid_phone_attempts,
            "normalized_phone": normalized_phone,
            "partner_count": 0,
            "partner": None,
            "matched_partners": [],
        }

    if partner_count == 1:
        return {
            "status": "existing_client",
            "next_step": "check_active_leads",
            "message": "Thank you. I found your existing profile and will check your ongoing enquiries.",
            "invalid_phone_attempts": invalid_phone_attempts,
            "normalized_phone": normalized_phone,
            "partner_count": 1,
            "partner": partners[0],
            "matched_partners": partners,
        }

    return {
        "status": "handover_multiple_matches",
        "next_step": "handover_agent",
        "message": "I found multiple profiles for this number. I'm connecting you with our team to continue safely.",
        "invalid_phone_attempts": invalid_phone_attempts,
        "normalized_phone": normalized_phone,
        "partner_count": partner_count,
        "partner": None,
        "matched_partners": partners,
    }