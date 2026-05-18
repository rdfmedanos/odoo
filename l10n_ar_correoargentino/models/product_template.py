# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_ar_length_cm = fields.Integer(string='Largo (cm)')
    l10n_ar_width_cm = fields.Integer(string='Ancho (cm)')
    l10n_ar_height_cm = fields.Integer(string='Alto (cm)')
