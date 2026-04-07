# -*- coding: utf-8 -*-
from odoo import fields, models


class RuhunutLeadSource(models.Model):
    """Reference model for the origin/channel through which a lead arrived."""

    _name = 'ruhunu.lead.source'
    _description = 'Lead Source'
    _order = 'sequence, name'

    name = fields.Char(
        string='Lead Source',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Lead source name must be unique.'),
    ]
