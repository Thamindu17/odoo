import re
from odoo.http import Controller, Response, request, route


class ThemeController(Controller):

    DEFAULT_PRIMARY_COLOR = '#875A7B'
    DEFAULT_SECONDARY_COLOR = '#00A09D'
    DEFAULT_FONT_FAMILY = 'inter'
    LUMINANCE_THRESHOLD = 0.35

    HEX_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')

    FONT_FAMILY_MAP = {
        'inter': 'Inter, system-ui, -apple-system, sans-serif',
        'roboto': 'Roboto, system-ui, -apple-system, sans-serif',
        'open_sans': 'Open Sans, system-ui, -apple-system, sans-serif',
        'lato': 'Lato, system-ui, -apple-system, sans-serif',
    }

    @route('/web/theme.css', auth='public', type='http', methods=['GET'])
    def theme_css(self):
        """Serve dynamic CSS with company branding colors and contrast-aware foreground."""
        company = request.env['res.company'].sudo().search([], limit=1)

        primary_color = self._validate_color(
            company.primary_color,
            self.DEFAULT_PRIMARY_COLOR
        )
        secondary_color = self._validate_color(
            company.secondary_color,
            self.DEFAULT_SECONDARY_COLOR
        )
        font_family = company.font_family or self.DEFAULT_FONT_FAMILY
        font_stack = self.FONT_FAMILY_MAP.get(font_family, self.FONT_FAMILY_MAP[self.DEFAULT_FONT_FAMILY])

        primary_foreground = self._calculate_foreground_color(primary_color)

        css_content = self._generate_css(
            primary_color=primary_color,
            primary_foreground=primary_foreground,
            secondary_color=secondary_color,
            font_family=font_stack,
            custom_css=company.ui_custom_css or ""
        )

        response = Response(css_content, mimetype='text/css')
        response.headers['Cache-Control'] = 'no-store'

        return response

    def _validate_color(self, color_value, default_value):
        """Validate hex color format, return default if invalid."""
        if not color_value or not self.HEX_PATTERN.match(color_value):
            return default_value
        return color_value

    def _hex_to_rgb(self, hex_color):
        """Convert hex color string to RGB tuple (0-1 range)."""
        hex_value = hex_color.lstrip('#')
        r = int(hex_value[0:2], 16) / 255.0
        g = int(hex_value[2:4], 16) / 255.0
        b = int(hex_value[4:6], 16) / 255.0
        return (r, g, b)

    def _linearize_channel(self, channel):
        """Linearize sRGB channel value for luminance calculation."""
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    def _calculate_luminance(self, hex_color):
        """Calculate relative luminance using WCAG formula."""
        r, g, b = self._hex_to_rgb(hex_color)

        r_linear = self._linearize_channel(r)
        g_linear = self._linearize_channel(g)
        b_linear = self._linearize_channel(b)

        luminance = (0.2126 * r_linear) + (0.7152 * g_linear) + (0.0722 * b_linear)
        return luminance

    def _calculate_foreground_color(self, hex_color):
        """Determine foreground color based on background luminance."""
        luminance = self._calculate_luminance(hex_color)

        if luminance < self.LUMINANCE_THRESHOLD:
            return '#FFFFFF'
        return '#1A1A1A'

    def _generate_css(self, primary_color, primary_foreground, secondary_color, font_family, custom_css):
        """Generate CSS content with custom properties and additional rules."""
        css_template = """:root {{
    --primary-color: {primary_color};
    --primary-foreground: {primary_foreground};
    --secondary-color: {secondary_color};
    --font-family: {font_family};
}}

/* Custom User CSS */
{custom_css}
"""
        return css_template.format(
            primary_color=primary_color,
            primary_foreground=primary_foreground,
            secondary_color=secondary_color,
            font_family=font_family,
            custom_css=custom_css
        )
