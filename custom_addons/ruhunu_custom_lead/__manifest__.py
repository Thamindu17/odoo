# -*- coding: utf-8 -*-
{
    'name': 'Ruhunu Custom Lead',
    'version': '19.0.1.0.0',
    'summary': 'Extended CRM Lead with Client Demographics & Maternity Logic',
    'description': """
Ruhunu Custom Lead
==================
Extends the standard Odoo CRM Lead/Opportunity form with:

- Lead source and category classification
- Comprehensive client demographics (NIC, DOB, computed age, gender, insurance, VIP …)
- Conditional **Maternity Details** section (visible only when category = "Maternity")
- Client follow-up tracking (interest / choice)
- Appointment confirmation
- Closure remark and mandatory lost-reason enforcement
- Reference data management: Lead Sources, Lead Categories, Cities, Occupations
    """,
    'author': 'Ruhunu',
    'category': 'Sales/CRM',
    'depends': ['crm', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/crm_lead_product_catalogue_views.xml',
        'views/crm_lead_line_views.xml',
        'views/ruhunu_lead_source_views.xml',
        'views/crm_lead_category_views.xml',
        'views/ruhunu_city_views.xml',
        'views/ruhunu_occupation_views.xml',
        'views/ruhunu_first_contact_response_views.xml',
        'views/ruhunu_relation_to_client_views.xml',
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ruhunu_custom_lead/static/src/css/ruhunu_lead_form.css',
            'ruhunu_custom_lead/static/src/js/ruhunu_lead_autosave.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
