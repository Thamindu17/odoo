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

Notes
- Odoo API key is used as the XML-RPC password.
- Archive is safer than hard delete for CRM records.
