# -*- coding: utf-8 -*-
"""
crm.lead.product.catalogue
===========================
Transient wizard opened by the "Catalogue" button in the Revenue Tracking
tab.  Allows the operator to select multiple products from the standard
Odoo product catalogue and add them all as revenue lines in one step.
"""
from odoo import api, fields, models


class CrmLeadProductCatalogue(models.TransientModel):
    _name = 'crm.lead.product.catalogue'
    _description = 'CRM Lead — Add Products from Catalogue'

    # ------------------------------------------------------------------ #
    #  Fields                                                              #
    # ------------------------------------------------------------------ #
    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string='Lead / Opportunity',
        required=True,
        ondelete='cascade',
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='lead_id.company_id',
        readonly=True,
    )
    product_ids = fields.Many2many(
        comodel_name='product.product',
        string='Products',
        domain="[('sale_ok', '=', True)]",
        help='Select one or more products to add to the Revenue Tracking tab.',
    )

    # ================================================================== #
    #  Action                                                              #
    # ================================================================== #

    def action_add_products(self):
        """
        Create one crm.lead.line for every selected product.

        Design notes
        ~~~~~~~~~~~~
        * Uses ``model_create_multi`` via a single ``create()`` call for
          efficiency — one SQL INSERT instead of N.
        * Taxes are filtered to the lead's company so that multi-company
          setups work correctly.
        * Falls back gracefully when ``get_product_multiline_description_sale``
          is not available (i.e. the ``sale`` module is not installed).
        """
        self.ensure_one()
        if not self.product_ids:
            return {'type': 'ir.actions.act_window_close'}

        company = self.lead_id.company_id or self.env.company
        lines_vals = []

        for product in self.product_ids:
            # Build description ----------------------------------------
            if hasattr(product, 'get_product_multiline_description_sale'):
                name = product.get_product_multiline_description_sale()
            else:
                name = product.name or ''
                if product.description_sale:
                    name = '%s\n%s' % (name, product.description_sale)

            # Filter taxes to current company -------------------------
            taxes = product.taxes_id.filtered(
                lambda t: t.company_id == company
            )

            lines_vals.append({
                'lead_id': self.lead_id.id,
                'product_id': product.id,
                'name': name,
                'product_uom_qty': 1.0,
                'price_unit': product.lst_price,
                'product_uom_id': product.uom_id.id,
                'tax_id': [(6, 0, taxes.ids)],
            })

        self.env['crm.lead.line'].create(lines_vals)
        return {'type': 'ir.actions.act_window_close'}
