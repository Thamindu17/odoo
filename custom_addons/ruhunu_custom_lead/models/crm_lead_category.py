# -*- coding: utf-8 -*-
from odoo import fields, models


class RuhunutLeadCategory(models.Model):
    """Classifies a lead into a service category (e.g. Maternity, General, etc.).

    The "Maternity Details" section on the CRM lead form becomes visible
    automatically whenever a category whose name equals "Maternity"
    (case-insensitive) is selected.
    """

    _name = 'ruhunu.lead.category'
    _description = 'Lead Category'
    _order = 'sequence, name'

    name = fields.Char(
        string='Lead Category',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Lead category name must be unique.'),
    ]
