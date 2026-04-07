# -*- coding: utf-8 -*-
from odoo import fields, models


class RuhunutOccupation(models.Model):
    """Occupation reference table used on the CRM lead client card."""

    _name = 'ruhunu.occupation'
    _description = 'Occupation'
    _order = 'name'

    name = fields.Char(
        string='Occupation',
        required=True,
        translate=True,
    )
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Occupation name must be unique.'),
    ]
