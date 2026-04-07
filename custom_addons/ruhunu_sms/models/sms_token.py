# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RuhunuSmsToken(models.Model):
    _name = 'ruhunu.sms.token'
    _description = 'Dialog eSMS Access Token'
    _order = 'id desc'

    token = fields.Text(string='Access Token', readonly=True)
    refresh_token = fields.Text(string='Refresh Token', readonly=True)
    expiration_time = fields.Datetime(string='Expiration Time', readonly=True)
    refresh_expiration_time = fields.Datetime(string='Refresh Expiration', readonly=True)
    is_active = fields.Boolean(string='Is Active', default=True, readonly=True)
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    wallet_balance = fields.Float(string='Wallet Balance', readonly=True)
    default_mask = fields.Char(string='Default Mask', readonly=True)
    user_mobile = fields.Char(string='User Mobile', readonly=True)
    user_email = fields.Char(string='User Email', readonly=True)

    @api.depends('expiration_time')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = record.expiration_time and record.expiration_time < now

    def get_valid_token(self):
        self.ensure_one()
        if self.is_expired:
            return False
        return self.token

    @api.model
    def get_active_token(self):
        active_token = self.search([('is_active', '=', True)], limit=1, order='id desc')
        if active_token and not active_token.is_expired:
            return active_token
        return False

    def action_deactivate_all(self):
        self.search([]).write({'is_active': False})
