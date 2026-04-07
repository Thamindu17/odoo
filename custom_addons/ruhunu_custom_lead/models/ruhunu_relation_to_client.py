# -*- coding: utf-8 -*-
from odoo import fields, models


class RuhunutRelationToClient(models.Model):
    """Reference table for the patient's relationship to the guardian/client.

    Examples: Father, Mother, Spouse, Sibling, Son, Daughter, Grandparent …
    """

    _name = 'ruhunu.relation.to.client'
    _description = 'Relation to Client'
    _order = 'sequence, name'

    name = fields.Char(
        string='Relation to Client',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Relation to Client name must be unique.'),
    ]
