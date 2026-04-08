from __future__ import annotations

import json
import re
from typing import Any

import requests
from requests.exceptions import RequestException

from .config import Settings


SYSTEM_PROMPT = (
    "You convert user CRM commands into strict JSON only. "
    "Output exactly one object with keys: action and payload. "
    "Allowed actions: create_lead, list_leads, update_lead, archive_lead, unknown. "
    "payload must be an object. Do not include markdown."
)

ENTITY_EXTRACTION_PROMPT = (
    "Extract chatbot requirement-gathering entities from one user message and return strict JSON only. "
    "Keys: first_name, last_name, title, city, requirement_summary, lead_category_suggestion, human_request. "
    "title must be one of mr, ms, dr, prof, rev when available. "
    "lead_category_suggestion must be one of Maternity, Wellness, Surgery, CAG, MRI when confidently inferred, else null. "
    "Support English, Sinhala, and Singlish transliteration. "
    "Use null for missing values. human_request must be true only if the user asks for a human/agent."
)

CATEGORY_CLASSIFICATION_PROMPT = (
    "Classify the healthcare requirement text into one category and return strict JSON only. "
    "Output format: {\"category\": <value_or_null>}. "
    "Allowed category values only: Maternity, Wellness, Surgery, CAG, MRI. "
    "If unclear, return null. "
    "Understand English, Sinhala, and Singlish transliteration. Do not include markdown."
)

SUMMARY_TO_ENGLISH_PROMPT = (
    "Rewrite the healthcare requirement into concise professional English for CRM lead summary and return strict JSON only. "
    "Output format: {\"summary\":\"...\"}. "
    "Input may be English, Sinhala, or Singlish transliteration. "
    "Keep intent and medical meaning accurate. Prefer one short sentence. Do not include markdown."
)

REQUIREMENT_REPLY_PROMPT = (
    "You are a healthcare CRM assistant. Generate one concise user-facing reply in JSON only. "
    "Output format: {\"message\":\"...\"}. "
    "Keep message under 160 characters where possible. "
    "Be polite, clear, and action-oriented. Do not include markdown."
)

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


class GeminiClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _extract_json(self, text: str) -> dict[str, Any]:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {"action": "unknown", "payload": {}}

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {"action": "unknown", "payload": {}}

    def _call_gemini_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.settings.gemini_api_key:
            return {}

        model = self.settings.gemini_model
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.settings.gemini_api_key}"
        )

        body = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt},
                        {"text": user_prompt},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 256,
            },
        }

        response = requests.post(endpoint, json=body, timeout=30)
        response.raise_for_status()
        data = response.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return {}

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts)
        return self._extract_json(text)

    def _infer_with_rules(self, message: str) -> dict[str, Any]:
        text = message.strip()
        lower = text.lower()

        create_lead_hint = re.search(
            r"\b(create|add|new|register)\b.*\b(lead|opportunity)\b|\b(lead|opportunity)\b.*\b(create|add|new|register)\b",
            lower,
        )
        if create_lead_hint:
            payload: dict[str, Any] = {}

            # Example supported: "Add a lead for Ahmed, company is Nova"
            person_match = re.search(
                r"(?:lead|opportunity)\s+for\s+([^,.;]+?)(?:\s*,|\s+company\s+is\s+|\s+from\s+|\s+at\s+|$)",
                text,
                flags=re.IGNORECASE,
            )
            company_match = re.search(
                r"(?:company\s+is\s+|from\s+|at\s+)([^,.;]+)",
                text,
                flags=re.IGNORECASE,
            )
            email_match = re.search(
                r"\b([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})\b",
                text,
                flags=re.IGNORECASE,
            )
            phone_match = re.search(
                r"(?:phone\s*(?:is|=|:)?\s*)?(\+?\d[\d\s\-()]{6,}\d)",
                text,
                flags=re.IGNORECASE,
            )
            revenue_match = re.search(
                r"(?:expected\s+revenue\s*(?:is|=|to)?\s*)([0-9]+(?:\.[0-9]+)?)",
                lower,
            )

            person_name = person_match.group(1).strip() if person_match else ""
            company_name = company_match.group(1).strip() if company_match else ""

            if person_name and company_name:
                payload["name"] = f"{person_name} - {company_name}"
                payload["description"] = f"Lead from company: {company_name}"
            elif person_name:
                payload["name"] = person_name
            elif company_name:
                payload["name"] = f"Lead - {company_name}"
                payload["description"] = f"Lead from company: {company_name}"

            if email_match:
                payload["email_from"] = email_match.group(1).strip()
            if phone_match:
                payload["phone"] = phone_match.group(1).strip()
            if revenue_match:
                payload["expected_revenue"] = float(revenue_match.group(1))

            if payload.get("name"):
                return {"action": "create_lead", "payload": payload}

        latest = re.search(r"(?:latest|last)\s+(\d+)\s+leads", lower)
        if latest:
            return {"action": "list_leads", "payload": {"limit": int(latest.group(1))}}

        if re.search(r"(?:latest|last)\s+leads", lower):
            return {"action": "list_leads", "payload": {"limit": 5}}

        update_revenue = re.search(
            r"update\s+lead\s+(.+?)\s+and\s+set\s+expected\s+revenue\s+to\s+([0-9]+(?:\.[0-9]+)?)",
            text,
            flags=re.IGNORECASE,
        )
        if update_revenue:
            return {
                "action": "update_lead",
                "payload": {
                    "lead_name": update_revenue.group(1).strip(),
                    "expected_revenue": float(update_revenue.group(2)),
                },
            }

        return {"action": "unknown", "payload": {}}

    def _infer_with_gemini(self, message: str) -> dict[str, Any]:
        parsed = self._call_gemini_json(SYSTEM_PROMPT, message)
        if not parsed:
            return {"action": "unknown", "payload": {}}
        return parsed

    def extract_requirement_entities(self, message: str) -> dict[str, Any]:
        text = message.strip()
        fallback = {
            "first_name": None,
            "last_name": None,
            "title": None,
            "city": None,
            "requirement_summary": None,
            "lead_category_suggestion": None,
            "human_request": False,
        }
        if not text:
            return fallback

        try:
            parsed = self._call_gemini_json(ENTITY_EXTRACTION_PROMPT, text)
            if not isinstance(parsed, dict):
                return fallback
        except RequestException:
            parsed = {}

        result = dict(fallback)
        for key in ["first_name", "last_name", "title", "city", "requirement_summary", "lead_category_suggestion"]:
            value = parsed.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                result[key] = stripped or None

        human_value = parsed.get("human_request")
        if isinstance(human_value, bool):
            result["human_request"] = human_value
        elif isinstance(human_value, str):
            result["human_request"] = human_value.strip().lower() in {"true", "yes", "1"}

        if not result["human_request"]:
            lower = text.lower()
            result["human_request"] = any(
                token in lower
                for token in ["human", "agent", "representative", "customer care", "operator"]
            )

        return result

    def _fallback_requirement_reply(self, intent: str, field_name: str | None, context: dict[str, Any]) -> str:
        first_name = str(context.get("first_name") or "").strip()
        lead_reference = str(context.get("lead_reference") or "").strip()

        if intent == "ask_field":
            return FALLBACK_FIELD_PROMPTS.get(field_name or "", "Could you please share more details?")
        if intent == "retry_field":
            return FALLBACK_FIELD_REASK.get(field_name or "", "Could you please clarify that?")
        if intent == "ack_and_ask":
            next_prompt = FALLBACK_FIELD_PROMPTS.get(field_name or "", "Could you please share the next detail?")
            if first_name and context.get("captured_field") == "first_name":
                return f"Thanks, {first_name}. {next_prompt}"
            return f"Thanks. {next_prompt}"
        if intent == "ready_to_create":
            return "Thank you. I have enough details to register your enquiry."
        if intent == "handover":
            return "I'm connecting you with a member of our team who can assist you further. Please hold."
        if intent == "missing_phone":
            return "I need a contact number before I can register your enquiry. I'm connecting you with our team."
        if intent == "completion":
            if first_name and lead_reference:
                return f"Thank you, {first_name}! Your enquiry is registered. Reference: {lead_reference}. Our team will contact you shortly."
            return "Thank you. Your enquiry has been registered. Our team will contact you shortly."
        if intent == "partial_timeout":
            return "Your enquiry has been saved with available details. Our team will follow up shortly."
        return "Thank you. We will continue with your enquiry."

    def compose_requirement_reply(
        self,
        intent: str,
        field_name: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> str:
        safe_context = context or {}

        # Terminal/sensitive intents must stay deterministic to avoid LLM drift.
        if intent in {"handover", "missing_phone", "completion", "partial_timeout", "ready_to_create"}:
            return self._fallback_requirement_reply(intent, field_name, safe_context)

        payload = {
            "intent": intent,
            "field_name": field_name,
            "context": safe_context,
            "allowed_fields": ["first_name", "last_name", "title", "city", "requirement_summary"],
        }
        prompt_text = json.dumps(payload, ensure_ascii=True)

        try:
            parsed = self._call_gemini_json(REQUIREMENT_REPLY_PROMPT, prompt_text)
        except RequestException:
            parsed = {}

        if isinstance(parsed, dict):
            message = parsed.get("message")
            if isinstance(message, str):
                cleaned = " ".join(message.split()).strip()
                if cleaned:
                    # Guard against intent drift: only accept LLM text for conversational intents.
                    if intent in {"ask_field", "retry_field", "ack_and_ask"}:
                        return cleaned[:280]

        return self._fallback_requirement_reply(intent, field_name, safe_context)

    def classify_requirement_category(self, requirement_text: str) -> str | None:
        text = requirement_text.strip()
        if not text:
            return None

        try:
            parsed = self._call_gemini_json(CATEGORY_CLASSIFICATION_PROMPT, text)
        except RequestException:
            parsed = {}

        if not isinstance(parsed, dict):
            return None

        value = parsed.get("category")
        if not isinstance(value, str):
            return None

        normalized = value.strip().lower()
        mapping = {
            "maternity": "Maternity",
            "wellness": "Wellness",
            "surgery": "Surgery",
            "cag": "CAG",
            "mri": "MRI",
        }
        return mapping.get(normalized)

    def summarize_requirement_english(self, requirement_text: str) -> str | None:
        text = requirement_text.strip()
        if not text:
            return None

        try:
            parsed = self._call_gemini_json(SUMMARY_TO_ENGLISH_PROMPT, text)
        except RequestException:
            parsed = {}

        if not isinstance(parsed, dict):
            return None

        summary = parsed.get("summary")
        if not isinstance(summary, str):
            return None

        cleaned = " ".join(summary.split()).strip()
        if not cleaned:
            return None
        return cleaned[:280]

    def infer_action(self, message: str) -> dict[str, Any]:
        try:
            parsed = self._infer_with_gemini(message)
        except RequestException:
            parsed = self._infer_with_rules(message)

        if "action" not in parsed:
            return self._infer_with_rules(message)
        if "payload" not in parsed or not isinstance(parsed["payload"], dict):
            parsed["payload"] = {}
        if parsed.get("action") == "unknown":
            return self._infer_with_rules(message)
        return parsed
