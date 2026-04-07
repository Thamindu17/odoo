# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class UiCustomField(models.Model):
    _name = 'ui.custom.field'
    _description = 'UI Custom Field'
    _order = 'sequence, id'
    _rec_name = 'field_name'

    name = fields.Char(
        string='Display Name',
        required=True,
        help='Human-readable name for the field'
    )
    field_name = fields.Char(
        string='Field Name',
        required=True,
        help='Technical field name (will be prefixed with x_)'
    )
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        domain=[('transient', '=', False), ('model', 'not like', 'ir.')],
        help='Target model for this custom field'
    )
    model_name = fields.Char(
        related='model_id.model',
        readonly=True,
        store=True,
        string='Model Name'
    )
    field_type = fields.Selection([
        ('char', 'Text'),
        ('integer', 'Integer'),
        ('float', 'Decimal'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('boolean', 'Boolean'),
        ('text', 'Long Text'),
        ('selection', 'Selection'),
        ('many2one', 'Many2One'),
        ('many2many', 'Many2Many'),
    ], string='Field Type', required=True, default='char')
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    required = fields.Boolean(
        string='Required',
        default=False,
        help='Make this field mandatory'
    )
    default_value = fields.Char(
        string='Default Value',
        help='Default value for new records'
    )
    help_text = fields.Char(
        string='Help Text',
        help='Tooltip text displayed for this field'
    )
    selection_options = fields.Char(
        string='Selection Options',
        help='Comma-separated options for selection fields (e.g., Option1,Option2,Option3)'
    )
    relation_model_id = fields.Many2one(
        'ir.model',
        string='Related Model',
        domain=[('transient', '=', False), ('model', 'not like', 'ir.')],
        help='Target model for many2one/many2many fields'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company this field applies to'
    )
    field_id = fields.Many2one(
        'ir.model.fields',
        string='Created Field',
        readonly=True,
        copy=False,
        ondelete='cascade'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('created', 'Created'),
        ('error', 'Error'),
    ], string='State', default='draft', readonly=True, tracking=True)
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )

    validation_ids = fields.One2many(
        'ui.field.validation',
        'custom_field_id',
        string='Validations'
    )

    _sql_constraints = [
        ('unique_field_model', 'UNIQUE(field_name, model_id)', 
         'Only one field with this name per model is allowed'),
    ]

    @api.constrains('field_name')
    def _check_field_name(self):
        """Validate field name format."""
        name_pattern = re.compile(r'^[a-z][a-z0-9_]*$')
        for record in self:
            if not name_pattern.match(record.field_name):
                raise ValidationError(_(
                    'Field name must start with a lowercase letter and contain '
                    'only lowercase letters, numbers, and underscores'
                ))
            if record.field_name.startswith('x_'):
                raise ValidationError(_(
                    'Do not include x_ prefix - it will be added automatically'
                ))
            if len(record.field_name) > 60:
                raise ValidationError(_('Field name must be less than 60 characters'))

    @api.constrains('selection_options')
    def _check_selection_options(self):
        """Validate selection options format."""
        for record in self:
            if record.field_type == 'selection' and record.selection_options:
                options = [opt.strip() for opt in record.selection_options.split(',') if opt.strip()]
                if not options:
                    raise ValidationError(_('Selection field must have at least one option'))

    @api.model
    def create(self, vals):
        result = super().create(vals)
        result._create_field()
        return result

    def write(self, vals):
        result = super().write(vals)
        if any(k in vals for k in ['field_type', 'required', 'default_value', 
                                    'selection_options', 'relation_model_id', 'active']):
            for record in self:
                if record.active:
                    record._update_field()
                else:
                    record._remove_field()
        return result

    def unlink(self):
        for record in self:
            record._remove_field()
        return super().unlink()

    def _get_full_field_name(self):
        """Get full field name with x_ prefix."""
        self.ensure_one()
        return 'x_%s' % self.field_name

    def _create_field(self):
        """Create the actual field in ir.model.fields."""
        self.ensure_one()
        try:
            full_name = self._get_full_field_name()
            
            existing = self.env['ir.model.fields'].search([
                ('model_id', '=', self.model_id.id),
                ('name', '=', full_name)
            ], limit=1)
            
            if existing:
                self.state = 'error'
                self.error_message = _('Field %s already exists') % full_name
                return

            field_vals = {
                'model_id': self.model_id.id,
                'name': full_name,
                'field_description': self.name,
                'ttype': self.field_type,
                'required': self.required,
                'help': self.help_text,
                'state': 'manual',
            }

            if self.default_value:
                field_vals['default'] = self.default_value

            if self.field_type == 'selection' and self.selection_options:
                options = [opt.strip() for opt in self.selection_options.split(',') if opt.strip()]
                selection = [(opt.lower().replace(' ', '_'), opt) for opt in options]
                field_vals['selection'] = str(selection)

            if self.field_type in ('many2one', 'many2many') and self.relation_model_id:
                field_vals['relation'] = self.relation_model_id.model

            field = self.env['ir.model.fields'].create(field_vals)
            self.field_id = field.id
            self.state = 'created'
            self.error_message = False

        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)

    def _update_field(self):
        """Update existing field."""
        self.ensure_one()
        if not self.field_id:
            self._create_field()
            return

        try:
            self.field_id.write({
                'field_description': self.name,
                'required': self.required,
                'help': self.help_text,
            })

            if self.default_value:
                self.field_id.default = self.default_value

            self.state = 'created'
            self.error_message = False

        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)

    def _remove_field(self, force=False):
        """Remove the created field if no data exists.
        
        Args:
            force: If True, remove even with data (use with caution)
        """
        self.ensure_one()
        if self.field_id:
            try:
                if not self.model_name:
                    self.field_id.unlink()
                    self.field_id = False
                    self.state = 'draft'
                    self.error_message = False
                    return
                
                model = self.env[self.model_name].sudo()
                
                if not force:
                    try:
                        self.env.cr.execute("""
                            SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL
                        """ % (model._table, self.field_id.name))
                        count = self.env.cr.fetchone()[0]
                        if count > 0:
                            self.state = 'draft'
                            self.error_message = _('Cannot delete field: %d records contain data') % count
                            return
                    except Exception as e:
                        self.state = 'draft'
                        self.error_message = _('Cannot check data: %s') % str(e)
                        return
                
                self.field_id.unlink()
            except Exception as e:
                self.state = 'draft'
                self.error_message = _('Failed to remove field: %s') % str(e)
                return
            self.field_id = False
        self.state = 'draft'
        self.error_message = False

    def action_create_field(self):
        """Manually trigger field creation."""
        self.ensure_one()
        self._create_field()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Field creation attempted. Check state for result.'),
                'type': 'info' if self.state == 'error' else 'success',
                'sticky': False,
            }
        }

    def action_check_field_data(self):
        """Check if field has data in database."""
        self.ensure_one()
        if not self.field_id or not self.model_name:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Field not created yet'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        
        try:
            model = self.env[self.model_name].sudo()
            self.env.cr.execute("""
                SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL
            """ % (model._table, self.field_id.name))
            count = self.env.cr.fetchone()[0]
            
            if count > 0:
                message = _('Field contains data in %d records. Cannot be safely removed.') % count
                msg_type = 'warning'
            else:
                message = _('Field has no data. Safe to remove.')
                msg_type = 'success'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': msg_type,
                    'sticky': True,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Error checking data: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def action_remove_field(self):
        """Remove field with safety check and confirmation."""
        self.ensure_one()
        
        if not self.field_id:
            self._remove_field()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Field removed successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
        
        if self.error_message and 'data' in self.error_message.lower():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': self.error_message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        self._remove_field()
        
        if self.state == 'draft' and self.error_message:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': self.error_message,
                    'type': 'warning',
                    'sticky': True,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('Field removed successfully'),
                'type': 'success',
                'sticky': False,
            }
        }


class UiFieldValidation(models.Model):
    _name = 'ui.field.validation'
    _description = 'UI Field Validation Rule'
    _order = 'sequence, id'

    name = fields.Char(
        string='Validation Name',
        required=True
    )
    custom_field_id = fields.Many2one(
        'ui.custom.field',
        string='Custom Field',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    validation_type = fields.Selection([
        ('regex', 'Regex Pattern'),
        ('min_max_numeric', 'Min/Max Numeric'),
        ('min_length', 'Minimum Length'),
        ('max_length', 'Maximum Length'),
    ], string='Validation Type', required=True)
    regex_pattern = fields.Char(
        string='Regex Pattern',
        help='Regular expression pattern for validation'
    )
    regex_message = fields.Char(
        string='Error Message',
        help='Error message shown when regex validation fails'
    )
    min_value = fields.Float(
        string='Minimum Value',
        help='Minimum numeric value'
    )
    max_value = fields.Float(
        string='Maximum Value',
        help='Maximum numeric value'
    )
    min_length = fields.Integer(
        string='Minimum Length',
        help='Minimum string length'
    )
    max_length = fields.Integer(
        string='Maximum Length',
        help='Maximum string length'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.constrains('validation_type', 'regex_pattern')
    def _check_regex_pattern(self):
        """Validate regex pattern."""
        for record in self:
            if record.validation_type == 'regex' and record.regex_pattern:
                try:
                    re.compile(record.regex_pattern)
                except re.error as e:
                    raise ValidationError(_('Invalid regex pattern: %s') % str(e))

    @api.constrains('min_value', 'max_value')
    def _check_min_max_values(self):
        """Validate min/max values."""
        for record in self:
            if record.validation_type == 'min_max_numeric':
                if record.min_value is not None and record.max_value is not None:
                    if record.min_value > record.max_value:
                        raise ValidationError(_('Minimum value cannot be greater than maximum value'))

    @api.constrains('min_length', 'max_length')
    def _check_min_max_length(self):
        """Validate min/max length."""
        for record in self:
            if record.validation_type in ('min_length', 'max_length'):
                if record.min_length is not None and record.min_length < 0:
                    raise ValidationError(_('Minimum length cannot be negative'))
                if record.max_length is not None and record.max_length < 0:
                    raise ValidationError(_('Maximum length cannot be negative'))
                if record.min_length is not None and record.max_length is not None:
                    if record.min_length > record.max_length:
                        raise ValidationError(_('Minimum length cannot be greater than maximum length'))
