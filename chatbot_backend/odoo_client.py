from __future__ import annotations

import xmlrpc.client
from typing import Any

from .client_identification import normalize_phone
from .config import Settings


class OdooClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._uid: int | None = None
        self._common = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/common")
        self._object = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/object")

    def authenticate(self) -> int:
        if self._uid:
            return self._uid
        uid = self._common.authenticate(
            self.settings.odoo_db,
            self.settings.odoo_login,
            self.settings.odoo_api_key,
            {},
        )
        if not uid:
            raise ValueError("Odoo authentication failed. Check ODOO_DB, ODOO_LOGIN, and ODOO_API_KEY.")
        self._uid = uid
        return uid

    def execute(self, model: str, method: str, *args: Any, **kwargs: Any) -> Any:
        uid = self.authenticate()
        return self._object.execute_kw(
            self.settings.odoo_db,
            uid,
            self.settings.odoo_api_key,
            model,
            method,
            list(args),
            kwargs,
        )

    def create_lead(self, vals: dict[str, Any]) -> int:
        return self.execute("crm.lead", "create", vals)

    def list_leads(self, domain: list[list[Any]], fields: list[str], limit: int) -> list[dict[str, Any]]:
        return self.execute("crm.lead", "search_read", domain, fields=fields, limit=limit)

    def update_lead(self, lead_id: int, vals: dict[str, Any]) -> bool:
        return self.execute("crm.lead", "write", [lead_id], vals)

    def archive_lead(self, lead_id: int) -> bool:
        return self.execute("crm.lead", "write", [lead_id], {"active": False})

    def search_individual_partners_by_phone(self, normalized_phone: str) -> list[dict[str, Any]]:
        fields = [
            "id",
            "name",
            "hp_first_name",
            "hp_last_name",
            "hp_salutation",
            "phone",
            "hp_whatsapp",
            "hp_city_category",
            "is_company",
        ]

        # Exact-match path for normalized data.
        exact_domain = [
            "&",
            "|",
            ["phone", "=", normalized_phone],
            ["hp_whatsapp", "=", normalized_phone],
            ["is_company", "=", False],
        ]
        exact_matches = self.execute("res.partner", "search_read", exact_domain, fields=fields, limit=20)
        if exact_matches:
            return exact_matches

        # Fallback path: pull likely candidates then normalize in Python.
        tail9 = normalized_phone[-9:]
        fallback_domain = [
            "&",
            "|",
            ["phone", "ilike", tail9],
            ["hp_whatsapp", "ilike", tail9],
            ["is_company", "=", False],
        ]
        candidates = self.execute("res.partner", "search_read", fallback_domain, fields=fields, limit=50)

        filtered: list[dict[str, Any]] = []
        for row in candidates:
            phone = normalize_phone(str(row.get("phone") or ""))
            whatsapp = normalize_phone(str(row.get("hp_whatsapp") or ""))
            if phone == normalized_phone or whatsapp == normalized_phone:
                filtered.append(row)

        return filtered

    def get_partner_profile(self, partner_id: int) -> dict[str, Any] | None:
        fields = ["id", "name", "hp_first_name", "hp_last_name", "phone", "hp_whatsapp"]
        try:
            rows = self.execute("res.partner", "search_read", [["id", "=", partner_id]], fields=fields, limit=1)
        except Exception:
            rows = self.execute("res.partner", "search_read", [["id", "=", partner_id]], fields=["id", "name"], limit=1)
        if not rows:
            return None
        return rows[0]

    def get_latest_active_lead_for_partner(self, partner_id: int) -> dict[str, Any] | None:
        domain = [
            ["partner_id", "=", partner_id],
            ["active", "=", True],
            ["stage_id.is_won", "=", False],
            ["stage_id.name", "not ilike", "lost"],
        ]
        fields = ["id", "name", "user_id", "stage_id", "ruhunu_lead_category_id", "create_date"]

        try:
            rows = self.execute("crm.lead", "search_read", domain, fields=fields, order="create_date desc", limit=1)
        except Exception:
            fallback_fields = ["id", "name", "user_id", "stage_id", "create_date"]
            rows = self.execute(
                "crm.lead",
                "search_read",
                domain,
                fields=fallback_fields,
                order="create_date desc",
                limit=1,
            )

        if not rows:
            return None
        return rows[0]

    def post_lead_chatter_note(self, lead_id: int, message: str) -> bool:
        result = self.execute(
            "crm.lead",
            "message_post",
            [lead_id],
            body=message,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )
        return bool(result)
