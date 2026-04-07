# -*- coding: utf-8 -*-
from odoo import fields, models


class RuhunutCity(models.Model):
    """Simple city reference table used on the CRM lead client card."""

    _name = 'ruhunu.city'
    _description = 'City'
    _order = 'name'

    name = fields.Char(
        string='City',
        required=True,
        translate=True,
    )
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'City name must be unique.'),
    ]
