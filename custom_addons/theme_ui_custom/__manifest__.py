{
    'name': 'Theme UI Custom',
    'version': '19.0.1.0.0',
    'category': 'Technical Settings',
    'summary': 'UI Customization Engine - Branding, Forms, Dynamic Fields',
    'description': """
Theme UI Custom
===============
Production-ready UI Customization Engine for Odoo 19.

Features:
---------
* Branding Customization (logos, colors, login page)
* Form Layout Customization with Visual Drag-and-Drop Builder
* Dynamic Field Creation (custom fields for any model)
* Field Validation Rules (required, regex, min/max)
* Robust XPath with True Tab Generation
* View Dry Run Validation for Safety
* Safe Uninstall Hook (preserves data)
* Multi-company support
* Security by design (admin-only configuration)

Version 19.0.1.0.0 - Phase 2 Improvements:
------------------------------------------
* Visual Form Layout Builder (OWL drag-and-drop widget)
* Robust XPath validation using lxml
* True tab generation with <page> elements
* Dry run validation before applying layouts
* Safe uninstall hook with data integrity checks
* Security group category updated to Administration

Usage:
------
Configure branding settings in Settings -> Companies -> [Select Company]
Manage form layouts in Settings -> UI Customization -> Form Layouts
Manage custom fields in Settings -> UI Customization -> Custom Fields
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/default_data.xml',
        'views/res_company_views.xml',
        'views/ui_form_layout_views.xml',
        'views/ui_custom_field_views.xml',
        'views/web_login_template.xml',
        'views/web_assets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'theme_ui_custom/static/src/scss/theme.scss',
        ],
        'web.assets_backend': [
            'theme_ui_custom/static/src/scss/theme.scss',
            'theme_ui_custom/static/src/scss/form_layout_builder.scss',
            'theme_ui_custom/static/src/js/form_layout_builder.js',
            'theme_ui_custom/static/src/xml/form_layout_builder.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': '_post_init_hook',
    'uninstall_hook': '_uninstall_hook',
}
