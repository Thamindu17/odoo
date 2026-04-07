# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RuhunuSmsTemplate(models.Model):
    _name = 'ruhunu.sms.template'
    _inherit = ['mail.thread']
    _description = 'SMS Template for Lead Communication'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    content = fields.Text(
        string='Message Content',
        required=True,
        help='SMS message content. Use placeholders like {{first_name}}, {{appointment_date}}, {{phone_number}}, {{hospital_name}}',
    )
    active = fields.Boolean(string='Active', default=True)
    category = fields.Selection(
        selection=[
            ('general', 'General'),
            ('appointment', 'Appointment'),
            ('follow_up', 'Follow Up'),
            ('feedback', 'Feedback'),
        ],
        string='Category',
        default='general',
    )
    description = fields.Text(string='Description', help='Brief description of when to use this template')

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Template name must be unique!'),
    ]

    def name_get(self):
        result = []
        for template in self:
            name = template.name
            if template.category:
                name = f"[{template.category}] {name}"
            result.append((template.id, name))
        return result
