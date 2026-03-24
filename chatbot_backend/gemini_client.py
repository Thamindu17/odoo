from __future__ import annotations

import json
import re
from typing import Any

import requests

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

    def infer_action(self, message: str) -> dict[str, Any]:
        if not self.settings.gemini_api_key:
            return {"action": "unknown", "payload": {}}

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent?key={self.settings.gemini_api_key}"
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
        parsed = self._extract_json(text)

        if "action" not in parsed:
            return {"action": "unknown", "payload": {}}
        if "payload" not in parsed or not isinstance(parsed["payload"], dict):
            parsed["payload"] = {}
        return parsed
