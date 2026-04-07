# -*- coding: utf-8 -*-
from odoo import fields, models


class RuhunutFirstContactResponse(models.Model):
    """Reference table for the outcome / response captured on first contact."""

    _name = 'ruhunu.first.contact.response'
    _description = 'First Contact Response'
    _order = 'sequence, name'

    name = fields.Char(
        string='First Contact Response',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'First Contact Response name must be unique.'),
    ]
