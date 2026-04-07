# Ruhunu SMS Module - Dialog eSMS Integration

## Overview

Odoo 19.0 addon for sending SMS via **Dialog eSMS API**. Credentials are hardcoded for private organization use.

## Features

- Send SMS from lead record (header button + Send SMS tab)
- **Dialog eSMS API v2** integration with token-based authentication
- **Automatic token management** - generates and refreshes tokens (valid 12 hours)
- 5 predefined hospital communication templates
- Editable phone number in Send SMS tab
- Full error code handling (100-118, 999)
- SMS logging with success/failure tracking
- Wallet balance tracking
- Unique transaction ID generation (prevents error 104)

## Requirements

- Odoo 19.0
- `ruhunu_custom_lead` module
- Dialog eSMS account

## Installation

### Step 1: Copy Module to Addons
```bash
cp -r ruhunu_sms /path/to/odoo/addons/
```

### Step 2: Update Apps List
1. Developer Mode: **Settings > General Settings > Developer Mode**
2. **Apps > Update Apps List**

### Step 3: Install
1. Search "Ruhunu SMS" in Apps
2. Click **Install**

### Step 4: Configure (Optional)
1. Go to **Settings** app
2. Scroll to **Ruhunu SMS Gateway (Dialog eSMS)**
3. Configure **Sender ID (Mask)** if different from default

> Credentials are hardcoded in code. Contact developer to change.

## Usage

### Send SMS from Lead

**Method 1: Header Button**
1. Open lead record
2. Ensure **Contact No** is filled
3. Click **Send SMS** button
4. Select template or write message (max 256 chars)
5. Click **Send Message**

**Method 2: Send SMS Tab**
1. Open lead record
2. Click **Send SMS** tab
3. Edit phone number if needed
4. Select template or write message
5. Click **Send Message**

### Token Management

Tokens are managed automatically:
- First SMS sends triggers token generation
- Token valid for **12 hours** (43200 seconds)
- Auto-refreshes on expiration
- View tokens: **CRM > Configuration > Access Tokens**

### Templates

Manage: **CRM > Configuration > SMS Templates**

#### Placeholders
| Placeholder | Replaced With |
|-------------|---------------|
| `{{first_name}}` | Lead's first name |
| `{{appointment_date}}` | Appointment date |
| `{{phone_number}}` | Contact number |
| `{{hospital_name}}` | Ruhunu Hospital |
| `{{link}}` | Feedback link |

### SMS Logs

View: **CRM > Configuration > SMS Logs** or from lead's SMS History button.

## Error Codes

| Code | Error | Resolution |
|------|-------|------------|
| 100 | Invalid Token (Token Expired) | Token auto-refreshes |
| 101 | Invalid Request Parameters | Check request format |
| 102 | User account not found | Verify credentials |
| 103 | Campaign not found | Check transaction ID |
| 104 | Transaction ID already used | Auto-generated (unique) |
| 105 | Invalid Token Signature | Token regenerated |
| 106 | Token not in header | Internal handling |
| 107 | Mandatory parameters missing | Check phone/message |
| 108 | No active mask | Configure Sender ID |
| 109 | No valid mobile numbers | Check phone format |
| 110 | Not eligible for packaging | Contact Dialog |
| 111 | Package only for current month | Use wallet payment |
| 112 | Insufficient messages in package | Top-up package |
| 113 | Package Maintenance Downtime | Wait for maintenance |
| 114 | Not enough wallet balance | Add funds |
| 115 | Username/password invalid | Check credentials |
| 116 | Account locked | Contact Dialog support |
| 117 | Too many requests | Wait and retry (TPS: 20) |
| 118 | System blackout (8PM-8AM) | Send outside blackout |
| 999 | Internal Server Error | Contact Dialog |

## API Details

### Endpoints
- **Login**: `https://e-sms.dialog.lk/api/v2/user/login`
- **Send SMS**: `https://e-sms.dialog.lk/api/v2/sms`

### Authentication Flow
```
POST /api/v2/user/login
Body: {"username": "AsthraGPapi", "password": "***"}
Response: {"token": "eyJ...", "expiration": 43200}
```

### Send SMS
```
POST /api/v2/sms
Headers: Authorization: Bearer <token>
Body: {
  "msisdn": [{"mobile": "714551682"}],
  "message": "Hello",
  "sourceAddress": "Ruhunu",
  "transaction_id": 123456789,
  "payment_method": 0
}
```

### Transaction IDs
- Auto-generated (timestamp-based)
- 1-18 digits
- Unique per request (prevents error 104)

### Phone Number Format
- Input: Any format (+94771234567, 0771234567, 771234567)
- Converted to: 9-digit format (7XXXXXXXX)

## Access Rights

| Model | Sales User | Sales Manager |
|-------|-----------|---------------|
| SMS Templates | Read | Full |
| SMS Logs | Read | Read/Write/Create |
| Access Tokens | Read | Full |
| Send SMS Wizard | Full | Full |

## Module Structure

```
ruhunu_sms/
├── __init__.py
├── __manifest__.py
├── README.md
├── data/
│   ├── sms_sequence_data.xml
│   └── sms_template_data.xml
├── models/
│   ├── __init__.py
│   ├── crm_lead.py
│   ├── sms_log.py
│   ├── sms_template.py
│   ├── sms_token.py
│   └── res_config_settings.py
├── security/
│   └── ir.model.access.csv
├── static/description/
│   └── icon.svg
├── views/
│   ├── crm_lead_views.xml
│   ├── sms_config_views.xml
│   ├── sms_log_views.xml
│   ├── sms_template_views.xml
│   └── sms_token_views.xml
└── wizard/
    ├── __init__.py
    ├── send_sms_wizard.py
    └── send_sms_wizard.xml
```

## Troubleshooting

**Token expired errors:**
- Check **CRM > Configuration > Access Tokens**
- Deactivate old tokens if needed

**Error 114 (Not enough balance):**
- Check wallet balance in token record
- Top-up via Dialog eSMS portal

**Error 118 (Blackout period):**
- System blackout: 8:00 PM - 8:00 AM (Sri Lanka time)
- Schedule SMS outside this window

**Error 104 (Transaction ID used):**
- Automatically handled (unique ID per request)
- Retry uses new transaction ID

## Support

Contact Ruhunu development team.

## License

LGPL-3

## Version

19.0.1.0.0
