import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    FONT_FAMILY_SELECTION = [
        ('inter', 'Inter'),
        ('roboto', 'Roboto'),
        ('open_sans', 'Open Sans'),
        ('lato', 'Lato'),
    ]

    ui_logo = fields.Image(
        string='Company Logo',
        attachment=True,
        help='Logo displayed in header and login page'
    )

    ui_login_background = fields.Image(
        string='Login Background',
        attachment=True,
        help='Background image for login page'
    )

    primary_color = fields.Char(
        string='Primary Color',
        default='#875A7B',
        help='Primary brand color used for main UI elements, buttons, and highlights. '
             'Accepts hex color format (e.g., #875A7B).'
    )

    secondary_color = fields.Char(
        string='Secondary Color',
        default='#00A09D',
        help='Secondary brand color used for accents, secondary buttons, and complementary '
             'UI elements. Accepts hex color format (e.g., #00A09D).'
    )

    font_family = fields.Selection(
        selection=FONT_FAMILY_SELECTION,
        string='Font Family',
        default='inter',
        help='Primary font family used throughout the backend interface. '
             'Choose from: Inter, Roboto, Open Sans, or Lato.'
    )

    ui_custom_css = fields.Text(
        string='Custom CSS',
        help='Additional custom CSS rules for advanced customization'
    )

    @api.onchange('ui_logo')
    def _onchange_ui_logo(self):
        if self.ui_logo:
            self.logo = self.ui_logo

    def write(self, vals):
        if 'ui_logo' in vals and vals['ui_logo']:
            vals['logo'] = vals['ui_logo']
        return super().write(vals)

    @api.constrains('primary_color', 'secondary_color')
    def _check_color_format(self):
        """Validate hex color format for primary and secondary colors."""
        hex_pattern = re.compile(r'^#[0-9A-Fa-f]{6}$')
        for record in self:
            for color_field in ['primary_color', 'secondary_color']:
                color_value = getattr(record, color_field)
                if color_value and not hex_pattern.match(color_value):
                    raise ValidationError(_(
                        'Invalid color format for %(field)s. '
                        'Please use hex format (e.g., #875A7B).',
                        field=record._fields[color_field].string
                    ))

    @api.constrains('ui_custom_css')
    def _check_custom_css(self):
        """Validate custom CSS for security."""
        for record in self:
            if record.ui_custom_css:
                if '<script' in record.ui_custom_css.lower():
                    raise ValidationError(_('Custom CSS cannot contain script tags'))
                if 'javascript:' in record.ui_custom_css.lower():
                    raise ValidationError(_('Custom CSS cannot contain javascript: protocol'))

    def _get_branding_css_vars(self):
        """Return CSS variables for branding."""
        self.ensure_one()
        
        # Calculate foreground color for primary based on luminance
        primary_color = self.primary_color or '#875A7B'
        
        # Simple luminance calculation for the template
        # (Using a simplified version of the controller logic)
        hex_val = primary_color.lstrip('#')
        r, g, b = tuple(int(hex_val[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        primary_foreground = '#FFFFFF' if luminance < 0.5 else '#1A1A1A'

        return {
            '--primary-color': primary_color,
            '--primary-foreground': primary_foreground,
            '--secondary-color': self.secondary_color or '#00A09D',
            '--font-family': self.FONT_FAMILY_MAP.get(self.font_family, 'Inter, sans-serif'),
        }

    FONT_FAMILY_MAP = {
        'inter': 'Inter, system-ui, -apple-system, sans-serif',
        'roboto': 'Roboto, system-ui, -apple-system, sans-serif',
        'open_sans': 'Open Sans, system-ui, -apple-system, sans-serif',
        'lato': 'Lato, system-ui, -apple-system, sans-serif',
    }
