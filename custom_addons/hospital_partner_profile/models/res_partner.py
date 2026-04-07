# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """
    Extends res.partner to add structured hospital CRM partner profiles.

    Design decisions:
    - Odoo's native is_company / company_type drives Person vs Company branching.
      This preserves full compatibility with CRM, Sales, and Contacts.
    - The auto-generated display label is stored in the native `name` field so
      that all Odoo search, Many2one dropdowns, and CRM lead linking work without
      patching.
    - `ref` (the Odoo built-in reference field) is reused for the unique
      Reference Number requirement, avoiding a redundant custom field.
    """

    _inherit = 'res.partner'

    # -------------------------------------------------------------------------
    # Person-specific fields
    # -------------------------------------------------------------------------

    hp_first_name = fields.Char(string='First Name')
    hp_last_name = fields.Char(string='Last Name')
    hp_salutation = fields.Selection(
        selection=[
            ('mr', 'Mr.'),
            ('ms', 'Ms.'),
            ('dr', 'Dr.'),
            ('prof', 'Prof.'),
            ('rev', 'Rev.'),
        ],
        string='Salutation',
    )
    hp_is_doctor = fields.Boolean(string='Is this a doctor?', default=False)
    hp_specialization = fields.Many2one(
        'hospital.partner.medical.specialization',
        string='Medical Specialization',
    )
    hp_is_vip = fields.Boolean(string='Is this a VIP?', default=False)
    hp_is_corporate = fields.Boolean(string='Is this Corporate?', default=False)
    hp_address_line1 = fields.Char(string='Address Line 1')
    hp_address_line2 = fields.Char(string='Address Line 2')
    hp_address_line3 = fields.Char(string='Address Line 3')
    hp_city_category = fields.Many2one(
        'hospital.partner.city',
        string='City',
    )
    hp_birthday = fields.Date(string='Birthday')
    hp_gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        string='Gender',
    )
    hp_nic = fields.Char(
        string='NIC',
    )
    hp_nic_normalized = fields.Char(
        string='NIC (Normalized)',
        compute='_compute_hp_nic_normalized',
        store=True,
        readonly=True,
    )
    hp_occupation = fields.Many2one('hospital.partner.occupation', string='Occupation')
    hp_employer = fields.Many2one('hospital.partner.employer', string='Employer')

    # -------------------------------------------------------------------------
    # Company-specific fields
    # -------------------------------------------------------------------------

    hp_company_name = fields.Char(string='Company Name')
    # `parent_id` reused as Parent Company (standard Odoo).

    hp_location = fields.Char(
        string='Location',
    )

    # -------------------------------------------------------------------------
    # Common fields
    # -------------------------------------------------------------------------

    # `phone` reused as Contact Number (standard Odoo).
    hp_whatsapp = fields.Char(string='WhatsApp Number')
    # `ref` (built-in) reused as Reference Number; uniqueness via SQL constraint.

    # -------------------------------------------------------------------------
    # Computed display name (stored → syncs into native `name`)
    # -------------------------------------------------------------------------

    hp_display_name_custom = fields.Char(
        string='Partner Title (Auto)',
        compute='_compute_hp_display_name',
        store=True,
    )

    # -------------------------------------------------------------------------
    # SQL constraints
    # -------------------------------------------------------------------------

    _sql_constraints = [
        (
            'hp_ref_unique',
            'UNIQUE(ref)',
            'The Reference Number (Ref) must be unique across all partners.',
        ),
    ]

    # -------------------------------------------------------------------------
    # Computed: build display name
    # -------------------------------------------------------------------------

    @api.depends(
        'company_type',
        'hp_company_name',
        'hp_location',
        'hp_first_name',
        'hp_last_name',
        'hp_nic',
    )
    def _compute_hp_display_name(self):
        """
        Company:  <Company Name> - <Location>
        Person:   <First Name> <Last Name> (<NIC>)

        Result is stored in hp_display_name_custom for display.
        The actual `name` field is kept in sync via create/write overrides
        so that Odoo search, Many2one, and CRM linking all work natively.
        """
        for partner in self:
            if partner.company_type == 'company':
                comp_name = (partner.hp_company_name or '').strip()
                loc = (partner.hp_location or '').strip()
                parts = [p for p in [comp_name, loc] if p]
                partner.hp_display_name_custom = ' - '.join(parts)
            elif partner.company_type == 'person':
                first = (partner.hp_first_name or '').strip()
                last = (partner.hp_last_name or '').strip()
                nic = (partner.hp_nic or '').strip()
                full = ' '.join(p for p in [first, last] if p)
                if nic:
                    full = f'{full} ({nic})' if full else nic
                partner.hp_display_name_custom = full
            else:
                partner.hp_display_name_custom = False

    # -------------------------------------------------------------------------
    # Sync `name` on create / write
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_type' in vals:
                vals['is_company'] = (vals['company_type'] == 'company')
            self._hp_sync_name(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'company_type' in vals:
            vals['is_company'] = (vals['company_type'] == 'company')
        self._hp_sync_name(vals, record=self)
        return super().write(vals)

    def _hp_sync_name(self, vals, record=None):
        """
        Derives and writes `name` from custom fields so that Odoo's native
        display name, search index, and Many2one resolution stay correct.

        For companies: name = <Company Name> - <Location>
        For persons:   name = <First Name> <Last Name> (<NIC>)

        Mutates `vals` in place.
        """
        rec = record[:1] if record else self.env['res.partner']
        is_company = vals.get('is_company', rec.is_company if rec else False)

        if is_company:
            company = str(vals.get('hp_company_name', rec.hp_company_name if rec else '') or '').strip()
            location = str(vals.get('hp_location', rec.hp_location if rec else '') or '').strip()

            parts = [p for p in [company, location] if p]
            if parts:
                vals['name'] = ' - '.join(parts)
        else:
            first = (vals.get('hp_first_name', rec.hp_first_name if rec else '') or '').strip()
            last = (vals.get('hp_last_name', rec.hp_last_name if rec else '') or '').strip()
            nic = (vals.get('hp_nic', rec.hp_nic if rec else '') or '').strip()
            parts = [p for p in [first, last] if p]
            full = ' '.join(parts)
            if nic:
                full = f'{full} ({nic})' if full else nic
            if full:
                vals['name'] = full

    # -------------------------------------------------------------------------
    # NIC normalization
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_nic_value(nic):
        """Convert a raw NIC string to the 12-digit normalized form.

        * 12 digits → returned unchanged.
        * 9 digits + V → converted: ``19`` + YY + DDD + ``0`` + SSSS
        * Empty / Invalid → returns *False*.
        """
        if not nic:
            return False
        nic = str(nic).strip().upper()
        if re.fullmatch(r'\d{12}', nic):
            return nic
        m = re.fullmatch(r'(\d{2})(\d{3})(\d{4})V', nic)
        if m:
            return f'19{m.group(1)}{m.group(2)}0{m.group(3)}'
        return False

    @api.depends('hp_nic')
    def _compute_hp_nic_normalized(self):
        """Store the 12-digit normalized NIC for search and duplicate checks."""
        for partner in self:
            partner.hp_nic_normalized = self._normalize_nic_value(partner.hp_nic)

    # -------------------------------------------------------------------------
    # Constraints: duplicate prevention
    # -------------------------------------------------------------------------

    @api.constrains(
        'company_type', 'hp_first_name', 'hp_last_name',
        'hp_nic', 'hp_company_name', 'hp_location',
    )
    def _check_duplicate_partner(self):
        """
        Person:  First Name + Last Name + NIC (normalized) must be unique.
        Company: Company Name + Location must be unique.
        """
        for partner in self:
            if partner.company_type == 'company':
                if not partner.hp_company_name or not partner.hp_location:
                    continue
                domain = [
                    ('is_company', '=', True),
                    ('hp_company_name', '=', partner.hp_company_name),
                    ('hp_location', '=', partner.hp_location),
                    ('id', '!=', partner.id),
                ]
                if self.search_count(domain):
                    raise ValidationError(_('This partner already exists.'))
            elif partner.company_type == 'person':
                if not partner.hp_nic_normalized:
                    continue
                domain = [
                    ('is_company', '=', False),
                    ('hp_nic_normalized', '=', partner.hp_nic_normalized),
                    ('id', '!=', partner.id),
                ]
                if self.search_count(domain):
                    raise ValidationError(_('A person with this NIC already exists.'))

    # -------------------------------------------------------------------------
    # NIC Constraints
    # -------------------------------------------------------------------------

    @api.constrains('hp_nic')
    def _check_hp_nic(self):
        """
        Validates the format of the National Identity Card (NIC).
        Must be exactly 12 digits (e.g., 199023456789)
        OR 9 digits plus uppercase V (e.g., 901234567V).
        """
        for partner in self:
            if partner.hp_nic:
                nic = partner.hp_nic.strip()
                if not re.fullmatch(r'\d{12}|\d{9}V', nic):
                    raise ValidationError(_(
                        'Invalid NIC format.\n'
                        'The NIC must be either:\n'
                        '- 12 digits (e.g., 199023456789)\n'
                        '- 9 digits followed by V (e.g., 901234567V)'
                    ))

    # -------------------------------------------------------------------------
    # Phone / WhatsApp Constraints
    # -------------------------------------------------------------------------

    @staticmethod
    def _validate_phone_number(value, field_label):
        """
        Validates that a phone value is exactly 10 digits and starts with '07'.
        Raises ValidationError if the value does not conform.
        Accepts blank / False values (field is not required by this constraint).
        """
        import re
        if value:
            v = value.strip()
            if not re.fullmatch(r'07\d{8}', v):
                raise ValidationError(_(
                    '%(label)s must be exactly 10 digits and start with 07 '
                    '(e.g. 0712345678). Received: %(value)s',
                    label=field_label,
                    value=v,
                ))

    @api.constrains('phone', 'hp_whatsapp')
    def _check_phone_numbers(self):
        for partner in self:
            self._validate_phone_number(partner.phone, _('Contact Number'))
            self._validate_phone_number(partner.hp_whatsapp, _('WhatsApp Number'))

    # -------------------------------------------------------------------------
    # Constraints: mandatory fields per partner type
    # -------------------------------------------------------------------------

    @api.constrains(
        'company_type', 'hp_company_name', 'hp_location', 'hp_first_name',
        'hp_last_name', 'hp_nic', 'hp_salutation', 'hp_birthday', 'phone',
        'hp_city_category'
    )
    def _check_required_fields(self):
        for partner in self:
            if partner.company_type == 'company':
                if not partner.hp_company_name:
                    raise ValidationError(_('Company Name is required for company partners.'))
                if not partner.hp_location:
                    raise ValidationError(_('Location is required for company partners.'))
            elif partner.company_type == 'person':
                if not partner.hp_first_name:
                    raise ValidationError(_('First Name is required for person partners.'))
                if not partner.hp_last_name:
                    raise ValidationError(_('Last Name is required for person partners.'))
                if not partner.hp_nic:
                    raise ValidationError(_('NIC is required for person partners.'))
                if not partner.hp_salutation:
                    raise ValidationError(_('Title is required for person partners.'))
                if not partner.hp_birthday:
                    raise ValidationError(_('Birthday is required for person partners.'))
                if not partner.phone:
                    raise ValidationError(_('Contact Number is required for person partners.'))
                if not partner.hp_city_category:
                    raise ValidationError(_('City is required for person partners.'))

    # -------------------------------------------------------------------------
    # Onchange: live UI feedback
    # -------------------------------------------------------------------------

    @api.onchange('hp_first_name', 'hp_last_name', 'hp_nic')
    def _onchange_person_name_fields(self):
        if self.company_type == 'person':
            first = (self.hp_first_name or '').strip()
            last = (self.hp_last_name or '').strip()
            nic = (self.hp_nic or '').strip()
            parts = [p for p in [first, last] if p]
            full = ' '.join(parts)
            if nic:
                full = f'{full} ({nic})' if full else nic
            self.name = full

    @api.onchange('hp_is_doctor')
    def _onchange_is_doctor(self):
        if self.hp_is_doctor:
            # Clear status fields that are incompatible with a doctor
            self.hp_is_vip = False
            self.hp_is_corporate = False
        # Always clear specialization when toggling off; keep clear on toggle on too
        self.hp_specialization = False

    @api.onchange('company_type')
    def _onchange_partner_type_clear_incompatible(self):
        """
        Prevent carry-over of values when switching between Person and Company.
        """
        if self.company_type == 'company':
            # Switched to Company: clear Person-specific fields and native name
            self.hp_first_name = False
            self.hp_last_name = False
            self.hp_salutation = False
            self.hp_is_doctor = False
            self.hp_specialization = False
            self.hp_is_vip = False
            self.hp_is_corporate = False
            self.hp_birthday = False
            self.hp_gender = False
            self.hp_nic = False
            self.hp_occupation = False
            self.hp_employer = False
            self.name = False
            self.phone = False
            self.hp_whatsapp = False
            self.email = False
            self.hp_address_line1 = False
            self.hp_address_line2 = False
            self.hp_address_line3 = False
            self.hp_city_category = False
        else:
            # Switched to Person: clear Company-specific fields
            self.hp_company_name = False
            self.hp_location = False
            self.parent_id = False
            self.name = False
            self.phone = False
            self.hp_whatsapp = False
            self.email = False
            self.hp_address_line1 = False
            self.hp_address_line2 = False
            self.hp_address_line3 = False
            self.hp_city_category = False
            self._onchange_person_name_fields()
