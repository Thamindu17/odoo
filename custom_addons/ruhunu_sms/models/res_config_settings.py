# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ruhunu_sms_gateway_sender_id = fields.Char(
        string='Sender ID',
        config_parameter='ruhunu_sms.gateway_sender_id',
        default='AsthraGP',
    )
