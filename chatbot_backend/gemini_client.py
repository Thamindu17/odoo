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

        model = self.settings.llm_model or self.settings.gemini_model
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

    def _infer_with_openai_compatible(self, message: str) -> dict[str, Any]:
        if not self.settings.llm_api_key:
            return {"action": "unknown", "payload": {}}
        if not self.settings.llm_model:
            raise ValueError("LLM_MODEL is required for openai-compatible provider")

        endpoint = f"{self.settings.llm_base_url.rstrip('/')}/chat/completions"
        body = {
            "model": self.settings.llm_model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        response = requests.post(endpoint, json=body, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            return {"action": "unknown", "payload": {}}

        text = choices[0].get("message", {}).get("content", "")
        return self._extract_json(text)

    def infer_action(self, message: str) -> dict[str, Any]:
        provider = self.settings.llm_provider.strip().lower()
        try:
            if provider == "openai-compatible":
                parsed = self._infer_with_openai_compatible(message)
            else:
                parsed = self._infer_with_gemini(message)
        except (RequestException, ValueError):
            parsed = self._infer_with_rules(message)

        if "action" not in parsed:
            return self._infer_with_rules(message)
        if "payload" not in parsed or not isinstance(parsed["payload"], dict):
            parsed["payload"] = {}
        if parsed.get("action") == "unknown":
            return self._infer_with_rules(message)
        return parsed
