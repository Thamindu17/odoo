# -*- coding: utf-8 -*-
{
    'name': 'Hospital Partner Profile',
    'version': '19.0.1.0.0',
    'summary': 'Structured partner profile management for hospital CRM',
    'description': """
        Extends res.partner to support structured partner profiles for a hospital CRM system.
        Supports Person and Company partner categories with hospital-specific fields,
        duplicate prevention, auto-generated partner titles, and CRM lead integration.
    """,
    'category': 'Healthcare/CRM',
    'author': 'Hospital CRM',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/hospital_master_data.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
