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
