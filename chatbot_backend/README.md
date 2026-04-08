Chatbot Backend (CRM Leads)

Purpose
- Connect chatbot requests to Odoo CRM (crm.lead) CRUD.
- Use Gemini to convert natural language into structured actions.

Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   pip install -r chatbot_backend/requirements.txt
3. Copy chatbot_backend/.env.example to chatbot_backend/.env and fill Odoo + Gemini values.

Run
- From repository root:
  uvicorn chatbot_backend.main:app --reload --port 8000

Endpoints
- GET /health
- POST /qualification/identify
- POST /qualification/active-lead-check
- POST /qualification/requirement-gathering
- POST /crm/create
- POST /crm/list
- POST /crm/update
- POST /crm/archive
- POST /chat/message

Section 3.1 Test (without WhatsApp API)
- Use /qualification/identify with simulated channel metadata phone or typed phone.
- Example payload (metadata phone available):
  {
    "channel_name": "internal_test",
    "metadata_phone": "+94 76 863 3308",
    "invalid_phone_attempts": 0
  }
- Example payload (bot asks for phone, then user provides):
  {
    "channel_name": "internal_test",
    "provided_phone": "0712345678",
    "invalid_phone_attempts": 1
  }

Section 3.2 Test (existing client active lead routing)
- Use /qualification/active-lead-check after 3.1 returns existing_client and partner id.
- Example payload:
  {
    "partner_id": 42,
    "channel_name": "internal_test"
  }
- Expected outcomes:
  - status=no_active_lead: continue requirement gathering
  - status=active_lead_found: bot notifies agent in chatter and ends conversation

Section 3.3 Test (requirement gathering + dummy-backed creation)
- Hybrid behavior:
  - Gemini agent 1: entity extraction (name/title/city/summary + human request intent)
  - Gemini agent 2: dynamic conversational reply composition
  - Deterministic policy engine: validation, retries, timeout, handover, and final Odoo writes
- Start conversation turn:
  {
    "flow_type": "new_client",
    "channel_name": "internal_test",
    "normalized_phone": "0770000001",
    "collected_data": {},
    "retry_counts": {}
  }
- Send user response for current field:
  {
    "flow_type": "new_client",
    "channel_name": "internal_test",
    "normalized_phone": "0770000001",
    "current_field": "first_name",
    "user_message": "Nimal",
    "collected_data": {},
    "retry_counts": {}
  }
- Continue until all required fields are captured; endpoint auto-creates partner+lead by default.
- To test conversation-only mode without creating records, set:
  {
    "auto_create_on_completion": false
  }
- For existing client with no active lead, use:
  {
    "flow_type": "existing_no_active",
    "channel_name": "internal_test",
    "normalized_phone": "0768633308",
    "partner_id": 7,
    "collected_data": {},
    "retry_counts": {}
  }

Notes
- Odoo API key is used as the XML-RPC password.
- Archive is safer than hard delete for CRM records.

Simple frontend tester
- Open chatbot_frontend/quick_test.html in a local static server (for example VS Code Live Server).
- Default backend URL in that page is http://127.0.0.1:9000.
- Use Start Session to begin 3.3 flow, Send for each user turn, and Create Now to trigger final create when auto-create is disabled.
