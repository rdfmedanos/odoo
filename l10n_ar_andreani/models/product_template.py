# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    andreani_length_cm = fields.Integer(string='Largo Andreani (cm)', help='Largo del producto en cm para cálculo de flete Andreani')
    andreani_width_cm = fields.Integer(string='Ancho Andreani (cm)', help='Ancho del producto en cm para cálculo de flete Andreani')
    andreani_height_cm = fields.Integer(string='Alto Andreani (cm)', help='Alto del producto en cm para cálculo de flete Andreani')
