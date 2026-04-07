# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    """Extends crm.lead with Ruhunu-specific demographics and maternity logic.

    Section layout (mirrors the form view):
        1. Lead Details
        2. Client Details
        3. Maternity Details  ← visible only when category name = "Maternity"
        4. Client Follow Up Updates
        5. Confirmation
        6. Closure
    """

    _inherit = 'crm.lead'

    # ──────────────────────────────────────────────────────────────────────────
    # Section 1 – Lead Details
    # ──────────────────────────────────────────────────────────────────────────

    ruhunu_lead_source_id = fields.Many2one(
        comodel_name='ruhunu.lead.source',
        string='Lead Source',
        ondelete='set null',
        tracking=True,
    )
    ruhunu_lead_category_id = fields.Many2one(
        comodel_name='ruhunu.lead.category',
        string='Lead Category',
        ondelete='set null',
        tracking=True,
    )
    ruhunu_lead_summary = fields.Char(string='Lead Summary')

    # ── Opportunity Name Auto-generation ──────────────────────────────────────
    # Recomputed whenever lead category or first name changes.
    # Format: <Category> / <First Name> / <Lead Created Date>
    # The name field on crm.lead is the "Opportunity Name"; we override the
    # compute so it stays in sync without blocking manual overrides later.
    name = fields.Char(
        compute='_compute_ruhunu_opportunity_name',
        store=True,
        readonly=False,   # allow manual override after creation
        depends=['ruhunu_lead_category_id', 'ruhunu_first_name', 'create_date'],
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Section 2 – Client Details
    # ──────────────────────────────────────────────────────────────────────────

    # F5: Rename partner_id to "Client" and restrict to individual contacts.
    # Only res.partner records that are *not* companies are selectable.
    partner_id = fields.Many2one(
        string='Client',
        domain=[('is_company', '=', False)],
    )

    ruhunu_client_title = fields.Char(string='Client Title')
    ruhunu_first_name = fields.Char(string='First Name')
    ruhunu_last_name = fields.Char(string='Last Name')
    ruhunu_nic = fields.Char(string='NIC')

    # F10 / F11
    ruhunu_birthday = fields.Date(string='Birthday')
    ruhunu_age = fields.Integer(
        string='Age',
        compute='_compute_ruhunu_age',
        store=True,
        readonly=True,
        help='Automatically calculated from the Birthday field.',
    )

    ruhunu_gender = fields.Selection(
        selection=[('male', 'Male'), ('female', 'Female')],
        string='Gender',
    )
    ruhunu_contact_no = fields.Char(string='Contact No')
    ruhunu_whatsapp_no = fields.Char(string='WhatsApp No')
    ruhunu_address = fields.Char(string='Address')
    ruhunu_city_id = fields.Many2one(
        comodel_name='ruhunu.city',
        string='City',
        ondelete='set null',
    )
    ruhunu_email = fields.Char(string='Email')

    # F18: any partner (individual or company) can be a referral source
    ruhunu_referred_by_id = fields.Many2one(
        comodel_name='res.partner',
        string='Referred By',
        ondelete='set null',
    )

    # F19 / F20 / F21 – Insurance
    ruhunu_has_insurance = fields.Boolean(
        string='Has Insurance?',
        default=False,
    )
    ruhunu_insurance_company_id = fields.Many2one(
        comodel_name='res.partner',
        string='Insurance Company',
        domain=[('is_company', '=', True)],
        ondelete='set null',
        help='Mandatory when "Has Insurance?" is enabled.',
    )
    ruhunu_insurance_exp_date = fields.Date(string='Insurance Exp Date')

    ruhunu_vip = fields.Boolean(string='VIP', default=False)
    ruhunu_occupation_id = fields.Many2one(
        comodel_name='ruhunu.occupation',
        string='Occupation',
        ondelete='set null',
    )
    ruhunu_employer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Employer',
        domain=[('is_company', '=', True)],
        ondelete='set null',
    )

    # F_CT: Client Type — Patient or Guardian
    # Defaults to 'patient' (preserves existing workflow).
    #   'guardian' → makes the Patient Details section visible.
    ruhunu_client_type = fields.Selection(
        selection=[
            ('patient', 'Patient'),
            ('guardian', 'Guardian'),
        ],
        string='Client is Patient or Guardian?',
        default='patient',
        tracking=True,
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Section 2.5 – Patient Details  (visible only when client_type = 'guardian')
    # ──────────────────────────────────────────────────────────────────────────

    ruhunu_patient_title = fields.Selection(
        selection=[
            ('mr', 'Mr.'),
            ('mrs', 'Mrs.'),
            ('ms', 'Ms.'),
            ('miss', 'Miss'),
            ('dr', 'Dr.'),
            ('master', 'Master'),
        ],
        string='Patient Title',
    )
    ruhunu_patient_first_name = fields.Char(string='Patient First Name')
    ruhunu_patient_last_name = fields.Char(string='Patient Last Name')
    ruhunu_patient_birthday = fields.Date(string='Patient Birthday')
    ruhunu_patient_age = fields.Integer(
        string='Patient Age',
        compute='_compute_ruhunu_patient_age',
        store=True,
        readonly=True,
        help='Automatically calculated from the Patient Birthday field.',
    )
    ruhunu_relation_to_client_id = fields.Many2one(
        comodel_name='ruhunu.relation.to.client',
        string='Relation to Client',
        ondelete='set null',
    )
    ruhunu_patient_gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ],
        string='Patient Gender',
    )
    ruhunu_patient_phone = fields.Char(string='Patient Phone No')
    ruhunu_patient_whatsapp = fields.Char(string='Patient WhatsApp No')

    # ──────────────────────────────────────────────────────────────────────────
    # Section 3 – Maternity Details
    # ──────────────────────────────────────────────────────────────────────────

    # UI flag: True when the selected lead category is "Maternity".
    # Stored so the value is always available to the form renderer without
    # a round-trip compute on every page load.
    ruhunu_is_maternity = fields.Boolean(
        string='Is Maternity',
        compute='_compute_ruhunu_is_maternity',
        store=True,
        help='Technical field – drives visibility of the Maternity Details section.',
    )
    ruhunu_expected_delivery_date = fields.Date(string='Expected Delivery Date')
    ruhunu_maternity_stage = fields.Selection(
        selection=[
            ('pre_conception', 'Pre-Conception'),
            ('1st_trimester', '1st Trimester'),
            ('2nd_trimester', '2nd Trimester'),
            ('3rd_trimester', '3rd Trimester'),
            ('post_natal', 'Post-Natal'),
        ],
        string='Maternity Stage',
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Section 4 – Client Follow Up Updates
    # ──────────────────────────────────────────────────────────────────────────

    # F_FC1 – First Contact Completion
    ruhunu_first_contact_done = fields.Boolean(
        string='First Contact Completion',
        default=False,
    )
    # F_FC2 – Mandatory when ruhunu_first_contact_done = True
    ruhunu_first_contacted_date = fields.Date(
        string='First Contacted Date',
        help='Mandatory when First Contact Completion is checked.',
    )
    # F_FC3 – Mandatory when ruhunu_first_contact_done = True
    ruhunu_first_contact_response_id = fields.Many2one(
        comodel_name='ruhunu.first.contact.response',
        string='First Contact Response',
        ondelete='set null',
        help='Mandatory when First Contact Completion is checked.',
    )

    ruhunu_client_interest = fields.Selection(
        selection=[('private', 'Private'), ('public', 'Public')],
        string='Client Interest',
    )
    ruhunu_client_choice = fields.Selection(
        selection=[('ruhunu', 'Ruhunu'), ('other', 'Other')],
        string='Client Choice',
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Section 5 – Confirmation
    # ──────────────────────────────────────────────────────────────────────────

    ruhunu_appointment_date = fields.Date(string='Appointment Date')

    # ──────────────────────────────────────────────────────────────────────────
    # Section 6 – Closure
    # ──────────────────────────────────────────────────────────────────────────

    ruhunu_closure_remark = fields.Char(string='Closure Remark')

    # lost_reason_id (Many2one → crm.lost.reason) already exists on crm.lead;
    # we reference it in the view and add a server-side constraint below.

    # UI flag: True when the current CRM stage is named "Lost" (case-insensitive).
    ruhunu_is_lost_stage = fields.Boolean(
        string='Is Lost Stage',
        compute='_compute_ruhunu_is_lost_stage',
        store=True,
        help='Technical field – enforces mandatory Lost Reason in the Closure section.',
    )

    # Added to control section visibility in the UI cleanly via XML
    ruhunu_stage_name = fields.Char(
        related='stage_id.name',
        string='Stage Name',
        store=True,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Revenue Tracking (previously in ruhunu_crm_revenue)
    # ─────────────────────────────────────────────────────────────────────────

    lead_line_ids = fields.One2many(
        comodel_name='crm.lead.line',
        inverse_name='lead_id',
        string='Revenue Lines',
        copy=True,
    )

    # Override: auto-compute from revenue lines when lines exist
    expected_revenue = fields.Monetary(
        compute='_compute_expected_revenue',
        store=True,
        readonly=False,
    )

    revenue_subtotal = fields.Monetary(
        string='Untaxed Revenue',
        compute='_compute_revenue_totals',
        store=True,
        currency_field='company_currency',
        help='Sum of all product line subtotals (taxes excluded).',
    )
    revenue_tax_total = fields.Monetary(
        string='Revenue Taxes',
        compute='_compute_revenue_totals',
        store=True,
        currency_field='company_currency',
        help='Total tax amount across all product lines.',
    )
    revenue_total = fields.Monetary(
        string='Revenue Total',
        compute='_compute_revenue_totals',
        store=True,
        currency_field='company_currency',
        help='Total revenue including taxes.',
    )

    # ──────────────────────────────────────────────────────────────────────────
    # Compute & Cron Methods
    # ──────────────────────────────────────────────────────────────────────────

    @api.depends(
        'lead_line_ids.price_subtotal',
        'lead_line_ids.price_tax',
        'lead_line_ids.price_total',
        'lead_line_ids.display_type',
    )
    def _compute_revenue_totals(self):
        """Aggregate revenue line amounts into lead-level totals."""
        for lead in self:
            product_lines = lead.lead_line_ids.filtered(
                lambda l: not l.display_type
            )
            lead.revenue_subtotal = sum(product_lines.mapped('price_subtotal'))
            lead.revenue_tax_total = sum(product_lines.mapped('price_tax'))
            lead.revenue_total = sum(product_lines.mapped('price_total'))

    @api.depends('revenue_total', 'lead_line_ids')
    def _compute_expected_revenue(self):
        """
        Auto-assign the Revenue Tracking total to Expected Revenue.
        If there are no lines, the field is left alone so the user can
        still type in an expected revenue manually.
        """
        for lead in self:
            if lead.lead_line_ids:
                lead.expected_revenue = lead.revenue_total

    def action_open_product_catalogue(self):
        """Open the Product Catalogue wizard to bulk-add products as revenue lines."""
        self.ensure_one()
        wizard = self.env['crm.lead.product.catalogue'].create({
            'lead_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Products from Catalogue',
            'res_model': 'crm.lead.product.catalogue',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
            'context': {'default_lead_id': self.id},
        }

    @api.model
    def _cron_update_maternity_stage(self):
        """Called daily by a scheduled action to update maternity stages."""
        leads = self.search([
            ('active', '=', True),
            ('probability', '<', 100),  # Not Won
            ('ruhunu_is_maternity', '=', True),
            ('ruhunu_expected_delivery_date', '!=', False)
        ])
        leads._update_maternity_stage_logic()

    def _update_maternity_stage_logic(self):
        """Core logic to determine and set maternity stage based on days to delivery."""
        today = fields.Date.today()
        for rec in self:
            if not rec.ruhunu_expected_delivery_date:
                continue
            days = (rec.ruhunu_expected_delivery_date - today).days
            if days > 270:
                stage = 'pre_conception'
            elif 180 <= days <= 270:
                stage = '1st_trimester'
            elif 90 <= days < 180:
                stage = '2nd_trimester'
            elif 0 <= days < 90:
                stage = '3rd_trimester'
            else:
                stage = 'post_natal'
            
            if rec.ruhunu_maternity_stage != stage:
                rec.ruhunu_maternity_stage = stage

    @api.onchange('ruhunu_expected_delivery_date')
    def _onchange_expected_delivery_date(self):
        """Immediately updates the UI stage when delivery date is tweaked manually."""
        self._update_maternity_stage_logic()

    @api.depends('ruhunu_lead_category_id.name', 'ruhunu_first_name', 'create_date')
    def _compute_ruhunu_opportunity_name(self):
        """Auto-generate Opportunity Name from: Category / First Name / Created Date.

        Falls back to today's date when create_date is not yet set (i.e. during
        a new-record compute cycle before the record is first saved to DB).
        """
        today_str = fields.Date.today().strftime('%Y-%m-%d')
        for rec in self:
            category = rec.ruhunu_lead_category_id.name or ''
            first_name = rec.ruhunu_first_name or ''
            if rec.create_date:
                date_str = rec.create_date.strftime('%Y-%m-%d')
            else:
                date_str = today_str
            if category or first_name:
                rec.name = f"{category} / {first_name} / {date_str}"
            # If neither category nor first_name is set yet, leave the name as-is
            # (avoid overwriting any manually typed value with an empty string).

    @api.depends('ruhunu_birthday')
    def _compute_ruhunu_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.ruhunu_birthday:
                rec.ruhunu_age = relativedelta(today, rec.ruhunu_birthday).years
            else:
                rec.ruhunu_age = 0

    @api.depends('ruhunu_patient_birthday')
    def _compute_ruhunu_patient_age(self):
        today = fields.Date.today()
        for rec in self:
            if rec.ruhunu_patient_birthday:
                rec.ruhunu_patient_age = relativedelta(today, rec.ruhunu_patient_birthday).years
            else:
                rec.ruhunu_patient_age = 0

    @api.depends('ruhunu_lead_category_id.name')
    def _compute_ruhunu_is_maternity(self):
        for rec in self:
            cat = rec.ruhunu_lead_category_id
            rec.ruhunu_is_maternity = bool(
                cat and cat.name and cat.name.strip().lower() == 'maternity'
            )

    @api.depends('stage_id.name')
    def _compute_ruhunu_is_lost_stage(self):
        for rec in self:
            stage = rec.stage_id
            rec.ruhunu_is_lost_stage = bool(
                stage and stage.name and stage.name.strip().lower() == 'lost'
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Onchange Methods
    # ──────────────────────────────────────────────────────────────────────────

    @api.onchange('ruhunu_first_contact_done')
    def _onchange_ruhunu_first_contact_done(self):
        """Automatically moves the lead to the 'Follow Up' pipeline stage when First Contact Completion is checked."""
        for rec in self:
            if rec.ruhunu_first_contact_done:
                follow_up_stage = self.env['crm.stage'].search([('name', '=ilike', 'follow up')], limit=1)
                if follow_up_stage:
                    rec.stage_id = follow_up_stage.id

    @api.onchange('partner_id')
    def _onchange_partner_id_ruhunu(self):
        """Auto-fill client details from the selected res.partner (live UX in the full form)."""
        for rec in self:
            if rec.partner_id:
                rec._ruhunu_sync_partner_fields()

    def _ruhunu_sync_partner_fields(self):
        """
        Core partner-sync logic — shared by the onchange (full form) and
        create() (quick create form).  Populates every client detail field
        from the linked res.partner / hospital_partner_profile data.

        Called in two contexts:
          1. @api.onchange('partner_id')  — real-time UI update on the full form.
          2. @api.model_create_multi override — server-side fill for leads
             created via the Kanban quick-create card (fields not on the card
             are absent from the view but are written in the same DB transaction).

        Falls back gracefully when hospital_partner_profile is not installed
        (safe getattr on every hp_* field).
        """
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return

        def get_f(fname):
            return getattr(partner, fname, False)

        # ── Scalar fields ────────────────────────────────────────────────
        if get_f('hp_salutation'):  self.ruhunu_client_title = get_f('hp_salutation')
        if get_f('hp_first_name'):  self.ruhunu_first_name   = get_f('hp_first_name')
        if get_f('hp_last_name'):   self.ruhunu_last_name    = get_f('hp_last_name')
        if get_f('hp_nic'):         self.ruhunu_nic          = get_f('hp_nic')
        if get_f('hp_birthday'):    self.ruhunu_birthday     = get_f('hp_birthday')
        if get_f('hp_gender'):      self.ruhunu_gender       = get_f('hp_gender')
        if get_f('phone'):          self.ruhunu_contact_no   = get_f('phone')
        if get_f('hp_whatsapp'):    self.ruhunu_whatsapp_no  = get_f('hp_whatsapp')
        if get_f('email'):          self.ruhunu_email        = get_f('email')
        if hasattr(partner, 'hp_is_vip'):
            self.ruhunu_vip = partner.hp_is_vip

        # ── Address ──────────────────────────────────────────────────────
        addr_parts = [
            str(getattr(partner, f, '') or '')
            for f in ('hp_address_line1', 'hp_address_line2', 'hp_address_line3')
            if getattr(partner, f, '')
        ]
        if addr_parts:
            self.ruhunu_address = ', '.join(addr_parts)

        # ── Relational fields — match by name, create on-the-fly if absent ──
        city = get_f('hp_city_category')
        if city and city.name:
            matched_city = self.env['ruhunu.city'].search([('name', '=ilike', city.name)], limit=1)
            if not matched_city:
                matched_city = self.env['ruhunu.city'].sudo().create({'name': city.name})
            self.ruhunu_city_id = matched_city.id
        else:
            self.ruhunu_city_id = False

        occ = get_f('hp_occupation')
        if occ and occ.name:
            matched_occ = self.env['ruhunu.occupation'].search([('name', '=ilike', occ.name)], limit=1)
            if not matched_occ:
                matched_occ = self.env['ruhunu.occupation'].sudo().create({'name': occ.name})
            self.ruhunu_occupation_id = matched_occ.id
        else:
            self.ruhunu_occupation_id = False

        emp = get_f('hp_employer')
        if emp and emp.name:
            matched_emp = self.env['res.partner'].search(
                [('name', '=ilike', emp.name), ('is_company', '=', True)], limit=1
            )
            if not matched_emp:
                matched_emp = self.env['res.partner'].sudo().create(
                    {'name': emp.name, 'is_company': True}
                )
            self.ruhunu_employer_id = matched_emp.id
        else:
            self.ruhunu_employer_id = False

    # ──────────────────────────────────────────────────────────────────────────
    # ORM Overrides
    # ──────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        """
        After normal record creation, run the partner-sync logic for any lead
        that was created with a partner_id (e.g. from the quick-create card).

        In the quick-create form only the visible fields are submitted.  Hidden
        fields such as ruhunu_whatsapp_no, ruhunu_email, ruhunu_city_id, etc.
        are absent from the submitted payload.  By calling
        _ruhunu_sync_partner_fields() server-side after creation we bridge that
        gap: the user never has to re-open and re-select the client.
        """
        records = super().create(vals_list)
        for record in records:
            if record.partner_id:
                # Use sudo() for the relational on-the-fly creates inside the
                # helper so that users with restricted access can still create
                # leads via the quick-create card.
                record.sudo()._ruhunu_sync_partner_fields()
            # Re-generate opportunity name now that create_date is available.
            # _compute_ruhunu_opportunity_name falls back to today() during
            # the initial compute (before DB flush), so we re-trigger once the
            # record is fully persisted and create_date is populated.
            record._compute_ruhunu_opportunity_name()
        return records

    @api.onchange('ruhunu_expected_delivery_date')
    def _onchange_ruhunu_expected_delivery_date(self):
        """Auto-suggest Maternity Stage from Expected Delivery Date.

        Boundary rules (days remaining until delivery, from today):
            > 270          → Pre-Conception
            181 – 270      → 1st Trimester
             91 – 180      → 2nd Trimester
              0 –  90      → 3rd Trimester
              < 0          → Post-Natal

        This is an onchange (not a stored compute) so the user can freely
        override the suggested value after the date is set.
        """
        for rec in self:
            if not rec.ruhunu_expected_delivery_date:
                # Clear the stage when the date is removed
                rec.ruhunu_maternity_stage = False
                continue

            today = fields.Date.today()
            days_remaining = (rec.ruhunu_expected_delivery_date - today).days

            if days_remaining > 270:
                rec.ruhunu_maternity_stage = 'pre_conception'
            elif days_remaining >= 181:
                rec.ruhunu_maternity_stage = '1st_trimester'
            elif days_remaining >= 91:
                rec.ruhunu_maternity_stage = '2nd_trimester'
            elif days_remaining >= 0:
                rec.ruhunu_maternity_stage = '3rd_trimester'
            else:
                rec.ruhunu_maternity_stage = 'post_natal'


    @api.constrains('ruhunu_contact_no')
    def _check_ruhunu_contact_no(self):
        for rec in self:
            if rec.ruhunu_contact_no:
                if len(rec.ruhunu_contact_no) != 10 or not rec.ruhunu_contact_no.isdigit() or not rec.ruhunu_contact_no.startswith('0'):
                    raise ValidationError(_('Contact No must be exactly 10 digits and start with 0.'))

    @api.constrains('ruhunu_lead_source_id')
    def _check_lead_source_required(self):
        for rec in self:
            if not rec.ruhunu_lead_source_id:
                raise ValidationError(_('Lead Source is mandatory. Please select a Lead Source before saving.'))

    @api.constrains('ruhunu_has_insurance', 'ruhunu_insurance_company_id')
    def _check_insurance_company_required(self):
        for rec in self:
            if rec.ruhunu_has_insurance and not rec.ruhunu_insurance_company_id:
                raise ValidationError(
                    _('Insurance Company is mandatory when "Has Insurance?" is enabled.')
                )

    @api.constrains(
        'ruhunu_first_contact_done',
        'ruhunu_first_contacted_date',
        'ruhunu_first_contact_response_id',
    )
    def _check_first_contact_fields_required(self):
        for rec in self:
            if rec.ruhunu_first_contact_done:
                if not rec.ruhunu_first_contacted_date:
                    raise ValidationError(
                        _('First Contacted Date is mandatory when First Contact Completion is checked.')
                    )
                if not rec.ruhunu_first_contact_response_id:
                    raise ValidationError(
                        _('First Contact Response is mandatory when First Contact Completion is checked.')
                    )

    @api.constrains('stage_id', 'lost_reason_id')
    def _check_lost_reason_required(self):
        for rec in self:
            if (
                rec.stage_id
                and rec.stage_id.name
                and rec.stage_id.name.strip().lower() == 'lost'
                and not rec.lost_reason_id
            ):
                raise ValidationError(
                    _('Lost Reason is mandatory when the pipeline stage is "Lost".')
                )

    def write(self, vals):
        """Override write to enforce appointment date and send soft warnings for other fields."""
        if 'stage_id' in vals:
            new_stage = self.env['crm.stage'].browse(vals['stage_id'])
            if new_stage and new_stage.name:
                stage_name = new_stage.name.strip().lower()
                for rec in self:
                    # Hard block: Appointment Date is mandatory for "Won"
                    if stage_name == 'won' or new_stage.is_won:
                        if not rec.ruhunu_appointment_date:
                            raise ValidationError(_(
                                'Appointment Date must be set before moving to "Won".'
                            ))

        res = super().write(vals)

        if 'stage_id' in vals:
            for rec in self:
                if not rec.stage_id or not rec.stage_id.name:
                    continue

                stage_name = rec.stage_id.name.strip().lower()

                # Soft warning: Moving to "Confirmation"
                if stage_name == 'confirmation':
                    missing = []
                    if rec.ruhunu_client_interest != 'private':
                        missing.append('• Client Interest should be "Private"')
                    if rec.ruhunu_client_choice != 'ruhunu':
                        missing.append('• Client Choice should be "Ruhunu"')
                    if missing:
                        rec._send_stage_warning(missing)

                # Soft warning: Moving to "Won"
                if stage_name == 'won' or rec.stage_id.is_won:
                    missing = []
                    if rec.ruhunu_client_interest != 'private':
                        missing.append('• Client Interest should be "Private"')
                    if rec.ruhunu_client_choice != 'ruhunu':
                        missing.append('• Client Choice should be "Ruhunu"')
                    if rec.expected_revenue <= 0:
                        missing.append('• Revenue details are missing')
                    if missing:
                        rec._send_stage_warning(missing)
        return res

    def _send_stage_warning(self, missing_items):
        """Send a non-blocking sticky warning notification via bus."""
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': _('Incomplete Lead Details'),
                'message': '\n'.join(missing_items),
                'type': 'warning',
                'sticky': True,
            },
        )
