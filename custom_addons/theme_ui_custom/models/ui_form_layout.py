# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from lxml import etree, objectify
import json
import re
import logging

_logger = logging.getLogger(__name__)


class UiFormLayout(models.Model):
    _name = 'ui.form.layout'
    _description = 'UI Form Layout Configuration'
    _order = 'sequence, id'
    _rec_name = 'name'

    name = fields.Char(
        string='Layout Name',
        required=True,
        help='Descriptive name for this layout configuration'
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        domain=[('transient', '=', False), ('model', 'not like', 'ir.')],
        help='Target model for this layout'
    )
    model_name = fields.Char(
        related='model_id.model',
        readonly=True,
        store=True,
        string='Model Name'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Lower values = higher priority'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Enable/disable this layout'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company this layout applies to'
    )
    layout_config = fields.Json(
        string='Layout Configuration',
        default='{}',
        help='JSON configuration for form layout'
    )
    view_id = fields.Many2one(
        'ir.ui.view',
        string='Generated View',
        readonly=True,
        copy=False,
        help='Auto-generated inherited view'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('error', 'Error'),
    ], string='State', default='draft', readonly=True, tracking=True)
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    available_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Available Fields',
        compute='_compute_available_fields'
    )

    _sql_constraints = [
        ('unique_model_company', 'UNIQUE(model_id, company_id)', 
         'Only one layout per model per company is allowed'),
    ]

    @api.depends('model_id')
    def _compute_available_fields(self):
        """Compute available fields for the target model."""
        for record in self:
            if record.model_id:
                fields_domain = [
                    ('model_id', '=', record.model_id.id),
                    ('name', 'not like', 'x_%'),
                    ('ttype', 'not in', ['one2many']),
                ]
                record.available_field_ids = self.env['ir.model.fields'].search(fields_domain)
            else:
                record.available_field_ids = False

    @api.constrains('layout_config')
    def _validate_layout_config(self):
        """Validate JSON structure of layout configuration."""
        for record in self:
            if not record.layout_config:
                continue
            try:
                config = record.layout_config
                if not isinstance(config, dict):
                    raise ValidationError(_('Layout configuration must be a JSON object'))
                if 'tabs' in config:
                    if not isinstance(config['tabs'], list):
                        raise ValidationError(_('Tabs must be an array'))
                    for idx, tab in enumerate(config['tabs']):
                        if not isinstance(tab, dict):
                            raise ValidationError(_('Tab %d must be an object') % idx)
                        if 'name' not in tab:
                            raise ValidationError(_('Each tab must have a name'))
                        if 'fields' in tab and not isinstance(tab['fields'], list):
                            raise ValidationError(_('Tab fields must be an array'))
                if 'fields' in config:
                    if not isinstance(config['fields'], list):
                        raise ValidationError(_('Fields must be an array'))
                    for field_name in config['fields']:
                        if not isinstance(field_name, str):
                            raise ValidationError(_('Field names must be strings'))
            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(_('Invalid JSON configuration: %s') % str(e))

    @api.model
    def create(self, vals):
        result = super().create(vals)
        if result.active:
            result._apply_layout(dry_run=False)
        return result

    def write(self, vals):
        result = super().write(vals)
        if 'active' in vals or 'layout_config' in vals or 'model_id' in vals:
            for record in self:
                if record.active:
                    record._apply_layout(dry_run=False)
                else:
                    record._remove_layout()
        return result

    def unlink(self):
        for record in self:
            record._remove_layout()
        return super().unlink()

    def _apply_layout(self, dry_run=False):
        """Generate inherited view from layout configuration.
        
        Args:
            dry_run: If True, only validate without creating view
        """
        self.ensure_one()
        try:
            view_model = self.env['ir.ui.view']
            
            if not dry_run and self.view_id:
                self.view_id.unlink()
                self.view_id = False

            base_view = self._find_base_view()
            if not base_view:
                self.state = 'error'
                self.error_message = _('No base view found for model %s') % self.model_name
                return False

            arch, validation_errors = self._generate_view_arch(base_view)
            
            if validation_errors:
                self.state = 'error'
                self.error_message = '\n'.join(validation_errors)
                return False

            if dry_run:
                try:
                    etree.fromstring(arch.encode('utf-8'))
                    self.state = 'draft'
                    self.error_message = _('Layout validation successful. Ready to apply.')
                    return True
                except etree.XMLSyntaxError as e:
                    self.state = 'error'
                    self.error_message = _('XML syntax error: %s') % str(e)
                    return False

            new_view = view_model.create({
                'name': '[UI Custom] %s' % self.name,
                'type': 'form',
                'model': self.model_name,
                'arch_db': arch,
                'inherit_id': base_view.id,
                'priority': 999,
                'active': True,
            })

            self.view_id = new_view.id
            self.state = 'applied'
            self.error_message = False
            return True

        except Exception as e:
            _logger.exception('Error applying layout: %s', e)
            self.state = 'error'
            self.error_message = str(e)
            return False

    def _remove_layout(self):
        """Remove generated view."""
        self.ensure_one()
        if self.view_id:
            try:
                self.view_id.unlink()
            except Exception:
                pass
            self.view_id = False
        self.state = 'draft'
        self.error_message = False

    def _find_base_view(self):
        """Find the base form view for the model."""
        view_model = self.env['ir.ui.view']
        base_views = view_model.search([
            ('model', '=', self.model_name),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
            ('mode', '=', 'primary'),
        ], limit=1, order='priority ASC, id ASC')
        return base_views

    def _validate_field_exists(self, model_name, field_name):
        """Check if a field exists in the model."""
        try:
            model = self.env[model_name]
            return field_name in model._fields
        except Exception:
            return False

    def _generate_view_arch(self, base_view):
        """Generate XML architecture for inherited view with robust XPath.
        
        Returns:
            tuple: (arch_xml, validation_errors)
        """
        validation_errors = []
        tabs = self.layout_config.get('tabs', [])
        fields_order = self.layout_config.get('fields', [])

        arch_parts = ['<data>']
        
        model = self.env[self.model_name]
        existing_fields = set(model._fields.keys())

        for field_name in fields_order:
            if field_name not in existing_fields:
                validation_errors.append(_('Field "%s" does not exist in model %s') % (field_name, self.model_name))
                continue
            
            arch_parts.append('''
                <xpath expr="//field[@name='%s']" position="attributes">
                    <attribute name="priority">999</attribute>
                </xpath>
            ''' % (field_name,))

        notebook_xpath = "//notebook"
        has_notebook = self._xpath_exists(base_view.arch_db, notebook_xpath)

        if tabs and has_notebook:
            for idx, tab in enumerate(tabs):
                tab_name = tab.get('name', 'Tab %d' % (idx + 1))
                tab_fields = tab.get('fields', [])
                
                if not tab_fields:
                    continue

                valid_tab_fields = []
                for field_name in tab_fields:
                    if field_name not in existing_fields:
                        validation_errors.append(_('Tab "%s": Field "%s" does not exist') % (tab_name, field_name))
                    else:
                        valid_tab_fields.append(field_name)

                if valid_tab_fields:
                    first_field = valid_tab_fields[0]
                    
                    field_pages = []
                    for field_name in valid_tab_fields:
                        field_pages.append('''
                            <field name="%s"/>''' % (field_name,))

                    arch_parts.append('''
                <xpath expr="%s" position="inside">
                    <page string="%s">
                        <group>%s
                        </group>
                    </page>
                </xpath>
                    ''' % (notebook_xpath, tab_name, ''.join(field_pages)))

                    for field_name in valid_tab_fields[1:]:
                        arch_parts.append('''
                <xpath expr="//page[@string='%s']//field[@name='%s']" position="after">
                    <field name="%s"/>
                </xpath>
                        ''' % (tab_name, first_field, field_name))

        elif tabs and not has_notebook:
            validation_errors.append(_('Model %s has no notebook element to add tabs') % self.model_name)

        arch_parts.append('</data>')
        return ''.join(arch_parts), validation_errors

    def _xpath_exists(self, xml_string, xpath_expr):
        """Check if an XPath expression matches in the XML."""
        try:
            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(xml_string.encode('utf-8'), parser)
            result = root.xpath(xpath_expr)
            return len(result) > 0
        except Exception:
            return False

    def action_validate_layout(self):
        """Dry run validation of layout."""
        self.ensure_one()
        success = self._apply_layout(dry_run=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': self.error_message or _('Layout validation successful'),
                'type': 'success' if success else 'danger',
                'sticky': True,
            }
        }

    def action_refresh_layout(self):
        """Manually refresh the layout."""
        self.ensure_one()
        self._apply_layout(dry_run=False)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Layout refreshed successfully') if self.state == 'applied' else _('Layout failed to apply'),
                'type': 'success' if self.state == 'applied' else 'danger',
                'sticky': False,
            }
        }

    def action_remove_layout(self):
        """Remove the generated layout."""
        self.ensure_one()
        self._remove_layout()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Layout removed successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def get_available_fields(self, model_id):
        """RPC method to get available fields for a model."""
        model = self.env['ir.model'].browse(model_id)
        if not model:
            return []
        
        fields = self.env['ir.model.fields'].search([
            ('model_id', '=', model_id),
            ('name', 'not like', 'x_%'),
            ('ttype', 'not in', ['one2many']),
        ])
        
        return [{'id': f.id, 'name': f.name, 'description': f.field_description} for f in fields]
