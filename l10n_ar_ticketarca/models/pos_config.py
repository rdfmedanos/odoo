# -*- coding: utf-8 -*-

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_ar_ticketarca_paper_width = fields.Selection(
        selection=[('58', '58 mm'), ('80', '80 mm')],
        string='Ancho ticket termica',
        default='80',
        help='Define el ancho del ticket para ajustar la impresion del bloque ARCA/AFIP.',
    )

    def _compute_defaultiface_print_auto(self):
        return True

    def write(self, vals):
        if 'iface_print_auto' not in vals and not self.env.context.get('install_mode'):
            configs_to_enable = self.search([('iface_print_auto', '=', False)])
            if configs_to_enable:
                configs_to_enable.write({'iface_print_auto': True})
        return super().write(vals)
