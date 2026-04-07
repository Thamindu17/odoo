# -*- coding: utf-8 -*-
{
    'name': 'Ruhunu SMS',
    'version': '19.0.1.0.0',
    'summary': 'Send SMS to Leads from CRM',
    'description': """
Ruhunu SMS
==========
Allows sales team to send SMS to leads using predefined templates or custom messages.

Features:
- Send SMS directly from lead record
- Predefined SMS templates for common scenarios
- Custom message support
- SMS sending history/log
- Integration with SMS gateway API

Templates included:
- Initial contact acknowledgment
- Appointment confirmation
- Missed appointment follow-up
- Post-visit care reminder
- Feedback request
    """,
    'author': 'Ruhunu',
    'category': 'Sales/CRM',
    'website': 'https://www.ruhunu.lk',
    'depends': [
        'base',
        'crm',
        'mail',
        'ruhunu_custom_lead',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sms_sequence_data.xml',
        'data/sms_template_data.xml',
        'views/sms_token_views.xml',
        'views/sms_config_views.xml',
        'views/sms_template_views.xml',
        'views/sms_log_views.xml',
        'views/crm_lead_views.xml',
        'wizard/send_sms_wizard.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
