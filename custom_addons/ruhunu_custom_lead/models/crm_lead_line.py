# -*- coding: utf-8 -*-
"""
crm.lead.line
=============
Revenue tracking line model — structurally mirrors sale.order.line so that
every sales-familiar concept (product, qty, price, taxes, section, note)
translates 1-to-1.  Depends only on crm + account (no sale required).

Attachment policy
-----------------
* Each product line may carry multiple attached files (bills, reports, etc.).
* Allowed types  : images, PDF, Excel (.xls/.xlsx), Word (.doc/.docx).
* Max size       : 20 MB per file (enforced server-side via @api.constrains).
* Section / note rows never carry attachments (cleared in ORM overrides).
"""
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class CrmLeadLine(models.Model):
    _name = 'crm.lead.line'
    _description = 'CRM Lead Revenue Line'
    _order = 'lead_id, sequence, id'

    # ------------------------------------------------------------------ #
    #  Attachment policy constants                                         #
    # ------------------------------------------------------------------ #
    # 20 MB in bytes
    _MAX_FILE_BYTES = 20 * 1024 * 1024

    # Accepted MIME type prefixes / exact values
    _ALLOWED_MIMETYPES = frozenset([
        'image/',                                                                    # any image
        'application/pdf',                                                           # PDF
        'application/vnd.ms-excel',                                                  # .xls
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',         # .xlsx
        'application/msword',                                                        # .doc
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',   # .docx
    ])

    # ------------------------------------------------------------------ #
    #  Relational                                                          #
    # ------------------------------------------------------------------ #
    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string='Lead / Opportunity',
        required=True,
        ondelete='cascade',
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='lead_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
    )

    # ------------------------------------------------------------------ #
    #  Layout / ordering                                                   #
    # ------------------------------------------------------------------ #
    sequence = fields.Integer(string='Sequence', default=10)

    display_type = fields.Selection(
        selection=[
            ('line_section', 'Section'),
            ('line_note', 'Note'),
        ],
        default=False,
        string='Display Type',
        help='Technical field used to render section separators and free-text '
             'notes inside the revenue lines list.',
    )

    # ------------------------------------------------------------------ #
    #  Product                                                             #
    # ------------------------------------------------------------------ #
    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        domain="[('sale_ok', '=', True)]",
        change_default=True,
        ondelete='restrict',
    )
    # Convenience – allows filtering from the product template kanban when
    # the product catalogue wizard is used.
    product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product Template',
        related='product_id.product_tmpl_id',
        readonly=True,
    )

    # ------------------------------------------------------------------ #
    #  Line description                                                    #
    # ------------------------------------------------------------------ #
    name = fields.Text(
        string='Description',
        required=True,
    )

    # ------------------------------------------------------------------ #
    #  Quantity & UoM                                                      #
    # ------------------------------------------------------------------ #
    product_uom_qty = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
        default=1.0,
    )
    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unit',
        ondelete='set null',
    )

    # ------------------------------------------------------------------ #
    #  Pricing                                                             #
    # ------------------------------------------------------------------ #
    price_unit = fields.Float(
        string='Unit Price',
        digits='Product Price',
        default=0.0,
    )
    tax_id = fields.Many2many(
        comodel_name='account.tax',
        relation='crm_lead_line_tax_rel',
        column1='line_id',
        column2='tax_id',
        string='Taxes',
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
    )

    # ------------------------------------------------------------------ #
    #  Computed amounts                                                    #
    # ------------------------------------------------------------------ #
    price_subtotal = fields.Monetary(
        string='Subtotal',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    price_tax = fields.Monetary(
        string='Tax Amount',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    price_total = fields.Monetary(
        string='Total',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )

    # ------------------------------------------------------------------ #
    #  Attachments                                                         #
    # ------------------------------------------------------------------ #
    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='crm_lead_line_attachment_rel',
        column1='line_id',
        column2='attachment_id',
        string='Attachments',
        help='Attach supporting files (bills, reports, images, etc.) '
             'to this revenue line.  Max 20 MB per file.  '
             'Allowed types: images, PDF, Excel, Word.',
    )
    attachment_count = fields.Integer(
        string='Files',
        compute='_compute_attachment_count',
        help='Number of files attached to this revenue line.',
    )

    # ================================================================== #
    #  Compute methods                                                     #
    # ================================================================== #

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        """Count attached files for display in the list column."""
        for line in self:
            line.attachment_count = len(line.attachment_ids)

    @api.depends('lead_id.company_id')
    def _compute_currency_id(self):
        """Derive line currency from the parent lead's company."""
        default_currency = self.env.company.currency_id
        for line in self:
            line.currency_id = (
                line.lead_id.company_id.currency_id or default_currency
            )

    @api.depends('product_uom_qty', 'price_unit', 'tax_id', 'currency_id', 'product_id')
    def _compute_amount(self):
        """
        Compute price_subtotal / price_tax / price_total using the standard
        Odoo tax engine (account.tax.compute_all).
        Section and note lines always yield zero amounts.
        """
        for line in self:
            if line.display_type:
                line.price_subtotal = 0.0
                line.price_tax = 0.0
                line.price_total = 0.0
                continue

            result = line.tax_id.compute_all(
                line.price_unit,
                currency=line.currency_id,
                quantity=line.product_uom_qty,
                product=line.product_id,
            )
            line.price_subtotal = result['total_excluded']
            line.price_tax = result['total_included'] - result['total_excluded']
            line.price_total = result['total_included']

    # ================================================================== #
    #  Onchange                                                            #
    # ================================================================== #

    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        Auto-fill description, unit price, UoM and default taxes when the
        operator picks a product.  Mirrors the behaviour in sale.order.line.
        """
        if not self.product_id:
            return

        product = self.product_id

        # --- Description ------------------------------------------------
        # Use sale description if available (requires 'sale' module),
        # otherwise fall back to product name + internal sales description.
        if hasattr(product, 'get_product_multiline_description_sale'):
            self.name = product.get_product_multiline_description_sale()
        else:
            name = product.name or ''
            if product.description_sale:
                name = '%s\n%s' % (name, product.description_sale)
            self.name = name

        # --- Price -------------------------------------------------------
        self.price_unit = product.lst_price

        # --- Unit of measure --------------------------------------------
        self.product_uom_id = product.uom_id

        # --- Taxes -------------------------------------------------------
        company = self.lead_id.company_id or self.env.company
        self.tax_id = product.taxes_id.filtered(
            lambda t: t.company_id == company
        )

    # ================================================================== #
    #  ORM overrides                                                       #
    # ================================================================== #

    def action_manage_attachments(self):
        """
        Open a minimal form popup so the user can upload / download files
        for this specific revenue line.

        Uses target='new' (modal dialog) so the user stays in context.
        The button that calls this method is type='object' inside an
        editable list — Odoo saves the current row automatically before
        executing server-side actions, so self.id is always a real int.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Line Attachments',
            'res_model': 'crm.lead.line',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'ruhunu_custom_lead.crm_lead_line_view_form_attachments'
            ).id,
            'target': 'new',
        }

    @api.constrains('attachment_ids')
    def _check_attachments(self):
        """
        Enforce file-size cap and allowed MIME types for every attachment
        linked to a product line.  Called automatically by the ORM on
        create / write whenever attachment_ids changes.
        """
        for line in self:
            for att in line.attachment_ids:
                # ---- Size check ----------------------------------------
                if att.file_size and att.file_size > self._MAX_FILE_BYTES:
                    raise ValidationError(
                        f'File "{att.name}" is {att.file_size / (1024*1024):.1f} MB. '
                        f'The maximum allowed size is 20 MB.'
                    )
                # ---- MIME type check -----------------------------------
                mimetype = (att.mimetype or '').lower()
                if mimetype and not any(
                    mimetype.startswith(allowed)
                    for allowed in self._ALLOWED_MIMETYPES
                ):
                    raise ValidationError(
                        f'File "{att.name}" has an unsupported type '
                        f'("{att.mimetype}"). '
                        f'Allowed types: images, PDF, Excel (.xls/.xlsx), '
                        f'Word (.doc/.docx).'
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Guarantee that section / note lines carry no product / pricing data
        regardless of what the caller passes in.
        """
        for vals in vals_list:
            if vals.get('display_type'):
                vals.update(
                    product_id=False,
                    product_uom_qty=0.0,
                    price_unit=0.0,
                    tax_id=[],
                    attachment_ids=[(5, 0, 0)],  # clear M2M
                )
        return super().create(vals_list)

    def write(self, vals):
        """Keep section / note lines clean when display_type is set later."""
        if vals.get('display_type'):
            vals.update(
                product_id=False,
                product_uom_qty=0.0,
                price_unit=0.0,
                tax_id=[(5, 0, 0)],          # clear M2M taxes
                attachment_ids=[(5, 0, 0)],  # clear M2M attachments
            )
        return super().write(vals)
