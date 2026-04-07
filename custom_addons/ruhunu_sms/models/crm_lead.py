# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    ruhunu_sms_log_ids = fields.One2many(
        comodel_name='ruhunu.sms.log',
        inverse_name='lead_id',
        string='SMS History',
        readonly=True,
    )
    ruhunu_sms_count = fields.Integer(
        string='SMS Count',
        compute='_compute_ruhunu_sms_count',
    )

    ruhunu_sms_tab_phone = fields.Char(
        string='Phone Number',
        compute='_compute_ruhunu_sms_tab_phone',
        inverse='_inverse_ruhunu_sms_tab_phone',
        help='Phone number for sending SMS. Editable in Send SMS tab.',
    )
    ruhunu_sms_tab_template_id = fields.Many2one(
        comodel_name='ruhunu.sms.template',
        string='SMS Template',
        domain=[('active', '=', True)],
        help='Select a template to auto-fill the message',
    )
    ruhunu_sms_tab_message = fields.Text(
        string='SMS Message',
        help='Write your message here or select a template',
    )

    @api.depends('ruhunu_contact_no')
    def _compute_ruhunu_sms_count(self):
        for lead in self:
            lead.ruhunu_sms_count = len(lead.ruhunu_sms_log_ids)

    @api.depends('ruhunu_contact_no')
    def _compute_ruhunu_sms_tab_phone(self):
        for lead in self:
            lead.ruhunu_sms_tab_phone = lead.ruhunu_contact_no

    def _inverse_ruhunu_sms_tab_phone(self):
        for lead in self:
            if lead.ruhunu_sms_tab_phone:
                lead.ruhunu_contact_no = lead.ruhunu_sms_tab_phone

    def action_view_sms_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('SMS History'),
            'res_model': 'ruhunu.sms.log',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {'default_lead_id': self.id},
            'target': 'current',
        }

    def action_send_sms(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send SMS'),
            'res_model': 'ruhunu.sms.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_phone_number': self.ruhunu_contact_no,
            },
        }

    @api.onchange('ruhunu_sms_tab_template_id')
    def _onchange_ruhunu_sms_tab_template_id(self):
        if self.ruhunu_sms_tab_template_id and self.ruhunu_sms_tab_template_id.content:
            self.ruhunu_sms_tab_message = self.ruhunu_sms_tab_template_id.content

    def action_send_sms_from_tab(self):
        self.ensure_one()
        phone = self.ruhunu_sms_tab_phone or self.ruhunu_contact_no
        
        if not phone:
            raise ValidationError(_("Phone number is required. Please enter a contact number."))
        if not self.ruhunu_sms_tab_message:
            raise ValidationError(_("Please enter a message to send."))
        
        wizard = self.env['ruhunu.sms.wizard'].create({
            'lead_id': self.id,
            'phone_number': phone,
            'template_id': self.ruhunu_sms_tab_template_id.id,
            'message': self.ruhunu_sms_tab_message,
        })
        
        self.ruhunu_sms_tab_template_id = False
        self.ruhunu_sms_tab_message = False
        
        return wizard.action_send_sms()
