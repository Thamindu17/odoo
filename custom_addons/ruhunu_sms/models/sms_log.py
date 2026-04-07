# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class RuhunuSmsLog(models.Model):
    _name = 'ruhunu.sms.log'
    _inherit = ['mail.thread']
    _description = 'SMS Sending Log'
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', required=True, readonly=True, copy=False)
    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string='Lead',
        required=True,
        ondelete='cascade',
        readonly=True,
    )
    phone_number = fields.Char(string='Phone Number', required=True, readonly=True)
    message = fields.Text(string='Message Sent', required=True, readonly=True)
    template_id = fields.Many2one(
        comodel_name='ruhunu.sms.template',
        string='Template Used',
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
        ],
        string='Status',
        default='draft',
        readonly=True,
        tracking=True,
    )
    error_code = fields.Char(string='Error Code', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)
    gateway_response = fields.Text(string='Gateway Response', readonly=True)
    sent_by_id = fields.Many2one(
        comodel_name='res.users',
        string='Sent By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    character_count = fields.Integer(string='Character Count', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('ruhunu.sms.log') or '/'
        return super().create(vals_list)

    def action_view_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lead'),
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
