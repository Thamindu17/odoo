# -*- coding: utf-8 -*-
import logging
import re
import urllib.request
import urllib.error
import json
import time
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


SMS_ERROR_CODES = {
    '100': _('Invalid Token (Token Expired)'),
    '101': _('Invalid Request Parameters'),
    '102': _('User account not found or not a valid account'),
    '103': _('Unable to find a campaign for the specified transaction ID'),
    '104': _('Transaction ID is already used'),
    '105': _('Invalid Token Signature'),
    '106': _('Token not found in the header (Or token is not attached as a bearer token)'),
    '107': _('One or more mandatory parameters in the request are missing or invalid'),
    '108': _('User does not have such active mask eligible to send messages'),
    '109': _('There is no single valid mobile number after removing invalids, duplicates and mask blocked numbers'),
    '110': _('Not eligible to consume packaging'),
    '111': _('Package payments can only be used for campaigns scheduled for this month'),
    '112': _('Number of messages left in the package is less than the campaign messages'),
    '113': _('Package Maintenance Downtime'),
    '114': _('Not enough wallet balance to run the campaign'),
    '115': _('Username or password invalid'),
    '116': _('Account locked'),
    '117': _('Too many requests'),
    '118': _('Campaigns cannot be created during the system blackout period (08:00 PM to 08:00 AM)'),
    '999': _('Internal Server Error'),
}

LOGIN_URL = 'https://e-sms.dialog.lk/api/v2/user/login'
SMS_URL = 'https://e-sms.dialog.lk/api/v2/sms'

# Dialog eSMS Credentials (Hardcoded for private organization use)
DIALOG_USERNAME = 'AsthraGPapi'
DIALOG_PASSWORD = 'G7v!pQ3rL8@xWz'
DIALOG_SENDER_ID = 'AsthraGP'


class RuhunuSmsWizard(models.TransientModel):
    _name = 'ruhunu.sms.wizard'
    _description = 'Wizard to Send SMS to Lead'

    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string='Lead',
        required=True,
        readonly=True,
    )
    phone_number = fields.Char(
        string='Phone Number',
        required=True,
        help='Recipient phone number. Auto-filled from lead contact number.',
    )
    template_id = fields.Many2one(
        comodel_name='ruhunu.sms.template',
        string='Template',
        domain=[('active', '=', True)],
        help='Select a template or write a custom message',
    )
    message = fields.Text(
        string='Message',
        required=True,
        help='SMS message content (max 256 characters)',
    )
    character_count = fields.Integer(
        string='Character Count',
        compute='_compute_character_count',
    )
    remaining_characters = fields.Integer(
        string='Characters Remaining',
        compute='_compute_character_count',
    )
    is_over_limit = fields.Boolean(
        string='Over Limit',
        compute='_compute_character_count',
    )

    _MAX_MESSAGE_LENGTH = 256

    @api.depends('message')
    def _compute_character_count(self):
        for wizard in self:
            count = len(wizard.message) if wizard.message else 0
            wizard.character_count = count
            wizard.remaining_characters = max(0, wizard._MAX_MESSAGE_LENGTH - count)
            wizard.is_over_limit = count > wizard._MAX_MESSAGE_LENGTH

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id and self.template_id.content:
            self.message = self.template_id.content

    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        if self.lead_id:
            self.phone_number = self.lead_id.ruhunu_contact_no

    @api.constrains('phone_number')
    def _check_phone_number(self):
        for wizard in self:
            if wizard.phone_number:
                cleaned = re.sub(r'[\s\-\(\)]', '', wizard.phone_number)
                if not re.match(r'^\+?\d{7,15}$', cleaned):
                    raise ValidationError(
                        _('Invalid phone number format. Please enter a valid phone number (7-15 digits).')
                    )

    @api.constrains('message')
    def _check_message_length(self):
        for wizard in self:
            if wizard.message and len(wizard.message) > self._MAX_MESSAGE_LENGTH:
                raise ValidationError(
                    _('Message exceeds maximum length of %d characters.') % self._MAX_MESSAGE_LENGTH
                )

    def _prepare_placeholders(self):
        self.ensure_one()
        lead = self.lead_id
        
        appointment_date = lead.ruhunu_appointment_date
        if isinstance(appointment_date, fields.Date):
            appointment_date = appointment_date.strftime('%Y-%m-%d')
        
        return {
            '{{first_name}}': lead.ruhunu_first_name or '',
            '{{lead_name}}': lead.ruhunu_first_name or '',
            '{{appointment_date}}': appointment_date or '',
            '{{phone_number}}': lead.ruhunu_contact_no or '',
            '{{hospital_name}}': 'Ruhunu Hospital',
            '{{link}}': '',
        }

    def _replace_placeholders(self, message):
        placeholders = self._prepare_placeholders()
        result = message
        for placeholder, value in placeholders.items():
            result = result.replace(placeholder, str(value))
        return result

    def _get_error_message(self, error_code):
        code_str = str(error_code)
        return SMS_ERROR_CODES.get(code_str, _('Unknown error (Code: %s)') % code_str)

    def _generate_unique_transaction_id(self):
        import random
        return int(time.time() * 1000) % (10 ** 18)

    def _get_or_refresh_token(self):
        self.ensure_one()
        
        gateway_username = DIALOG_USERNAME
        gateway_password = DIALOG_PASSWORD

        token_model = self.env['ruhunu.sms.token']
        active_token = token_model.get_active_token()
        
        if active_token and not active_token.is_expired:
            _logger.info('Using existing valid token')
            return active_token.token

        _logger.info('Generating new access token')
        
        try:
            payload = {
                'username': gateway_username,
                'password': gateway_password,
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                LOGIN_URL,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)

                _logger.info('Token Response: %s', result)

                if result.get('status') == 'success':
                    token = result.get('token')
                    expiration_seconds = result.get('expiration', 43200)
                    refresh_token = result.get('refreshToken')
                    refresh_expiration = result.get('refreshExpiration', 604800)
                    user_data = result.get('userData') or {}
                    
                    now = fields.Datetime.now()
                    expiration_time = now + timedelta(seconds=expiration_seconds)
                    refresh_exp_time = now + timedelta(seconds=refresh_expiration)
                    
                    token_model.action_deactivate_all()
                    
                    new_token = token_model.create({
                        'token': token,
                        'refresh_token': refresh_token,
                        'expiration_time': expiration_time,
                        'refresh_expiration_time': refresh_exp_time,
                        'is_active': True,
                        'wallet_balance': user_data.get('walletBalance') if user_data else 0,
                        'default_mask': user_data.get('defaultMask') if user_data else '',
                        'user_mobile': user_data.get('mobile') if user_data else '',
                        'user_email': user_data.get('email') if user_data else '',
                    })
                    
                    _logger.info('New token created, expires at: %s', expiration_time)
                    return token
                else:
                    error_code = result.get('errCode', 'UNKNOWN')
                    error_message = self._get_error_message(error_code)
                    raise UserError(_('Failed to get access token.\n\nError: %s') % error_message)

        except urllib.error.HTTPError as e:
            _logger.error('Token HTTP Error: %s - %s', e.code, e.reason)
            raise UserError(_('Failed to connect to SMS gateway for authentication. HTTP %s') % e.code)
        except urllib.error.URLError as e:
            _logger.error('Token URL Error: %s', e.reason)
            raise UserError(_('Cannot connect to SMS gateway. Please check your internet connection.'))
        except Exception as e:
            _logger.exception('Token Generation Unexpected Error')
            raise UserError(_('Unexpected error during authentication: %s') % str(e))

    def _send_sms_via_gateway(self, phone_number, message):
        self.ensure_one()
        
        gateway_sender_id = self.env['ir.config_parameter'].sudo().get_param('ruhunu_sms.gateway_sender_id', DIALOG_SENDER_ID)
        token = self._get_or_refresh_token()
        
        if not token:
            raise UserError(_('Failed to obtain access token. Please check credentials in Settings.'))

        try:
            cleaned_phone = re.sub(r'^\+?94|^\+?0', '', phone_number)
            cleaned_phone = re.sub(r'[\s\-\(\)]', '', cleaned_phone)
            
            if len(cleaned_phone) == 10 and cleaned_phone.startswith('0'):
                cleaned_phone = cleaned_phone[1:]
            
            transaction_id = self._generate_unique_transaction_id()
            
            payload = {
                'msisdn': [{'mobile': cleaned_phone}],
                'message': message,
                'sourceAddress': gateway_sender_id,
                'transaction_id': transaction_id,
                'payment_method': 0,
            }

            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                SMS_URL,
                data=data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}',
                },
                method='POST',
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)

                _logger.info('SMS Gateway Response: %s', result)

                if result.get('status') == 'success':
                    data_obj = result.get('data', {})
                    return {
                        'success': True,
                        'response': result,
                        'gateway_response': json.dumps(result, indent=2),
                        'campaign_id': data_obj.get('campaignId'),
                        'campaign_cost': data_obj.get('campaignCost'),
                        'wallet_balance': data_obj.get('walletBalance'),
                    }
                else:
                    error_code = result.get('errCode', result.get('error_code', 'UNKNOWN'))
                    error_message = self._get_error_message(error_code)
                    return {
                        'success': False,
                        'error_code': str(error_code),
                        'error_message': f'{error_code}: {error_message}',
                        'gateway_response': json.dumps(result, indent=2),
                    }

        except urllib.error.HTTPError as e:
            _logger.error('SMS Gateway HTTP Error: %s - %s', e.code, e.reason)
            try:
                error_body = e.read().decode('utf-8')
                error_data = json.loads(error_body)
                error_code = error_data.get('errCode', error_data.get('error_code', str(e.code)))
            except Exception:
                error_code = str(e.code)
            
            if e.code == 401:
                self.env['ruhunu.sms.token'].action_deactivate_all()
                error_message = _('Token expired or invalid. Token will be refreshed on next attempt.')
            else:
                error_message = self._get_error_message(error_code)
            
            return {
                'success': False,
                'error_code': error_code,
                'error_message': f'{error_code}: {error_message}',
                'gateway_response': f'HTTP {e.code}: {e.reason}',
            }

        except urllib.error.URLError as e:
            _logger.error('SMS Gateway URL Error: %s', e.reason)
            return {
                'success': False,
                'error_code': 'CONNECTION_ERROR',
                'error_message': _('CONNECTION_ERROR: %s') % e.reason,
                'gateway_response': str(e.reason),
            }

        except Exception as e:
            _logger.exception('SMS Gateway Unexpected Error')
            return {
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'error_message': _('INTERNAL_ERROR: %s') % str(e),
                'gateway_response': str(e),
            }

    def action_send_sms(self):
        self.ensure_one()

        if self.is_over_limit:
            raise ValidationError(_('Message exceeds maximum length of %d characters.') % self._MAX_MESSAGE_LENGTH)

        if not self.phone_number:
            raise ValidationError(_('Phone number is required.'))

        if not self.message:
            raise ValidationError(_('Message is required.'))

        final_message = self._replace_placeholders(self.message)

        if len(final_message) > self._MAX_MESSAGE_LENGTH:
            raise ValidationError(
                _('Message after placeholder replacement exceeds %d characters.') % self._MAX_MESSAGE_LENGTH
            )

        sms_log_vals = {
            'lead_id': self.lead_id.id,
            'phone_number': self.phone_number,
            'message': final_message,
            'template_id': self.template_id.id if self.template_id else False,
            'character_count': len(final_message),
        }

        sms_log = self.env['ruhunu.sms.log'].create(sms_log_vals)

        result = self._send_sms_via_gateway(self.phone_number, final_message)

        if result['success']:
            sms_log.write({
                'state': 'sent',
                'gateway_response': result.get('gateway_response', ''),
            })
            self.lead_id.message_post(
                body=_('SMS sent successfully to %s') % self.phone_number,
                message_type='comment',
            )
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('SMS sent successfully to %s') % self.phone_number,
                    'type': 'success',
                    'sticky': False,
                    'duration': 3,
                },
            }
        else:
            sms_log.write({
                'state': 'failed',
                'error_code': result.get('error_code', ''),
                'error_message': result.get('error_message', ''),
                'gateway_response': result.get('gateway_response', ''),
            })
            raise UserError(
                _('Failed to send SMS.\n\nError: %s') % result.get('error_message', _('Unknown error'))
            )
