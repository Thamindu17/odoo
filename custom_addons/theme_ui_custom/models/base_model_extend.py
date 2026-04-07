# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import ValidationError
import re

class BaseModelExtend(models.AbstractModel):
    _inherit = 'base'

    def _ui_custom_field_table_exists(self):
        """Check if the ui_custom_field table exists in the database.
        
        This prevents UndefinedTable errors when other modules are being
        installed or uninstalled and the table hasn't been created yet
        or has already been dropped.
        """
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'ui_custom_field'
            )
        """)
        return self.env.cr.fetchone()[0]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if 'ui.custom.field' in self.env and self._ui_custom_field_table_exists():
            for i, record in enumerate(records):
                keys = vals_list[i].keys() if i < len(vals_list) else []
                record._check_custom_ui_validations(list(keys))
        return records

    def write(self, vals):
        result = super().write(vals)
        if 'ui.custom.field' in self.env and self._ui_custom_field_table_exists():
            for record in self:
                record._check_custom_ui_validations(list(vals.keys()))
        return result

    def _check_custom_ui_validations(self, modified_fields=None):
        self.ensure_one()
        
        # Performance optimization: if no modified fields, skip.
        if modified_fields is not None and not modified_fields:
            return

        # Check if the model has custom fields registered
        custom_fields = self.env['ui.custom.field'].sudo().search([
            ('model_id.model', '=', self._name),
            ('active', '=', True),
            ('state', '=', 'created')
        ])
        
        if not custom_fields:
            return

        for custom_field in custom_fields:
            field_name = custom_field.field_id.name
            
            # Skip if field wasn't modified
            if modified_fields is not None and field_name not in modified_fields:
                continue
                
            # Safely get the value. False/None is standard for empty Odoo fields.
            value = getattr(self, field_name, False)
            
            # 1. Required Validation
            if custom_field.required and (value is False or value is None or value == ''):
                raise ValidationError(_("Field '%s' is required.") % custom_field.name)
            
            # Skip advanced validation if empty (unless required, which is caught above)
            if value is False or value is None or value == '':
                continue
                
            # 2. Custom Validations (Regex, Min/Max)
            for validation in custom_field.validation_ids.filtered('active'):
                
                # Regex Check
                if validation.validation_type == 'regex' and validation.regex_pattern:
                    if not re.match(validation.regex_pattern, str(value)):
                        msg = validation.regex_message or _("Invalid format for field '%s'.") % custom_field.name
                        raise ValidationError(msg)
                
                # Numeric Limits
                elif validation.validation_type == 'min_max_numeric' and isinstance(value, (int, float)):
                    if validation.min_value is not None and value < validation.min_value:
                        raise ValidationError(_("Value for '%s' must be at least %s.") % (custom_field.name, validation.min_value))
                    if validation.max_value is not None and value > validation.max_value:
                        raise ValidationError(_("Value for '%s' must be at most %s.") % (custom_field.name, validation.max_value))
                
                # String Length Limits
                elif validation.validation_type in ('min_length', 'max_length') and isinstance(value, str):
                    if validation.min_length is not None and len(value) < validation.min_length:
                        raise ValidationError(_("Length of '%s' must be at least %s characters.") % (custom_field.name, validation.min_length))
                    if validation.max_length is not None and len(value) > validation.max_length:
                        raise ValidationError(_("Length of '%s' must be at most %s characters.") % (custom_field.name, validation.max_length))
