Chatbot Backend (CRM Leads)

Purpose
- Connect chatbot requests to Odoo CRM (crm.lead) CRUD.
- Use Gemini to convert natural language into structured actions.

Setup
1. Create and activate a Python virtual environment.
2. Install dependencies:
   pip install -r chatbot_backend/requirements.txt
3. Copy chatbot_backend/.env.example to chatbot_backend/.env and fill values.

Run
- From repository root:
  uvicorn chatbot_backend.main:app --reload --port 8000

Endpoints
- GET /health
- POST /crm/create
- POST /crm/list
- POST /crm/update
- POST /crm/archive
- POST /chat/message

Notes
- Odoo API key is used as the XML-RPC password.
- Archive is safer than hard delete for CRM records.
