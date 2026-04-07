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
        if not self.settings.gemini_api_key:
            return {"action": "unknown", "payload": {}}

        model = self.settings.gemini_model
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={self.settings.gemini_api_key}"
        )

        body = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT},
                        {"text": message},
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
            return {"action": "unknown", "payload": {}}

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "\n".join(p.get("text", "") for p in parts)
        return self._extract_json(text)

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
