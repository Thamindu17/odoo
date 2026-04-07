from . import models
from . import controllers

from odoo import _
import logging

_logger = logging.getLogger(__name__)


def _post_init_hook(env):
    """Post installation hook to initialize default data."""
    _logger.info('theme_ui_custom: Running post init hook')
    
    try:
        company_model = env['res.company'].sudo()
        companies = company_model.search([])
        for company in companies:
            if not company.primary_color:
                company.primary_color = '#875A7B'
            if not company.secondary_color:
                company.secondary_color = '#00A09D'
            if not company.font_family:
                company.font_family = 'inter'
        _logger.info('theme_ui_custom: Default branding initialized')
    except Exception as e:
        _logger.warning('theme_ui_custom: Could not initialize defaults: %s', e)


def _uninstall_hook(env):
    """Uninstall hook to clean up customizations safely.
    
    Prevents data loss by:
    - Checking for existing data in custom fields
    - Only removing fields without data
    - Logging all actions for audit
    """
    _logger.info('theme_ui_custom: Running uninstall hook')
    cr = env.cr
    
    try:
        view_model = env['ir.ui.view'].sudo()
        custom_views = view_model.search([
            ('name', 'like', '[UI Custom]')
        ])
        if custom_views:
            custom_views.unlink()
            _logger.info('theme_ui_custom: Removed %d custom views', len(custom_views))
        
        custom_field_model = env['ui.custom.field'].sudo()
        custom_fields_records = custom_field_model.search([])
        
        fields_removed = 0
        fields_preserved = 0
        
        for record in custom_fields_records:
            if record.field_id and record.model_name:
                try:
                    model = env[record.model_name].sudo()
                    if record.field_id.name in model._fields:
                        can_remove = True
                        try:
                            cr.execute("""
                                SELECT COUNT(*) FROM %s WHERE %s IS NOT NULL
                            """ % (model._table, record.field_id.name))
                            count = cr.fetchone()[0]
                            if count > 0:
                                can_remove = False
                                _logger.warning(
                                    'theme_ui_custom: Preserving field %s.%s (has %d records with data)',
                                    record.model_name, record.field_id.name, count
                                )
                        except Exception as e:
                            _logger.warning(
                                'theme_ui_custom: Cannot check data for %s.%s: %s',
                                record.model_name, record.field_id.name, e
                            )
                            can_remove = False
                        
                        if can_remove:
                            try:
                                record.field_id.unlink()
                                fields_removed += 1
                                _logger.info(
                                    'theme_ui_custom: Removed field %s.%s',
                                    record.model_name, record.field_id.name
                                )
                            except Exception as e:
                                _logger.error(
                                    'theme_ui_custom: Failed to remove field %s.%s: %s',
                                    record.model_name, record.field_id.name, e
                                )
                                fields_preserved += 1
                        else:
                            fields_preserved += 1
                except Exception as e:
                    _logger.warning(
                        'theme_ui_custom: Error processing field %s: %s',
                        record.field_name, e
                    )
                    fields_preserved += 1
        
        _logger.info(
            'theme_ui_custom: Uninstall complete - Removed: %d fields, Preserved: %d fields',
            fields_removed, fields_preserved
        )
        
    except Exception as e:
        _logger.error('theme_ui_custom: Uninstall hook error: %s', e)

