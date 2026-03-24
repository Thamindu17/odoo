from __future__ import annotations

import xmlrpc.client
from typing import Any

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
