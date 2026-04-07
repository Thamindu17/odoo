from __future__ import annotations

from typing import Any, Callable


def _display_name(partner: dict[str, Any]) -> str:
    first = str(partner.get("hp_first_name") or "").strip()
    last = str(partner.get("hp_last_name") or "").strip()
    full = " ".join(part for part in [first, last] if part).strip()
    if full:
        return full
    return str(partner.get("name") or "Client").strip() or "Client"


def check_existing_client_active_lead(
    partner_id: int,
    channel_name: str,
    get_partner: Callable[[int], dict[str, Any] | None],
    get_latest_active_lead: Callable[[int], dict[str, Any] | None],
    post_lead_chatter: Callable[[int, str], bool],
) -> dict[str, Any]:
    partner = get_partner(partner_id) or {}
    lead = get_latest_active_lead(partner_id)

    if not lead:
        return {
            "status": "no_active_lead",
            "next_step": "requirement_gathering_existing",
            "client_message": "Thank you for reaching out. I will capture your current requirement and register a new enquiry.",
            "has_active_lead": False,
            "lead": None,
            "agent_name": None,
            "notification_posted": False,
            "end_conversation": False,
        }

    user_info = lead.get("user_id")
    if isinstance(user_info, (list, tuple)) and len(user_info) >= 2:
        agent_name = str(user_info[1] or "").strip() or "our sales team"
    else:
        agent_name = "our sales team"

    client_name = _display_name(partner)
    chatter_message = (
        f"Client {client_name} has reached out via {channel_name}. "
        "They may have a follow-up query regarding this lead. "
        "Please review and continue the conversation."
    )
    posted = post_lead_chatter(int(lead["id"]), chatter_message)

    if agent_name == "our sales team":
        client_message = (
            "Thank you for reaching out! I can see you already have an ongoing enquiry with us. "
            "I've notified our sales team, and someone will get back to you shortly."
        )
    else:
        client_message = (
            "Thank you for reaching out! I can see you already have an ongoing enquiry with us. "
            f"I've notified your dedicated agent, {agent_name}, who will get back to you shortly."
        )

    return {
        "status": "active_lead_found",
        "next_step": "notify_agent_and_end",
        "client_message": client_message,
        "has_active_lead": True,
        "lead": lead,
        "agent_name": agent_name,
        "notification_posted": posted,
        "end_conversation": True,
    }