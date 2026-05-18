# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .constants import CUSTOMER_VISIBLE_STATES


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_ar_correo_delivery_type = fields.Selection([
        ('D', 'Domicilio'),
        ('S', 'Sucursal'),
    ], string='Tipo de entrega Correo')
    l10n_ar_correo_destination_postal_code = fields.Char(string='CP destino Correo')
    l10n_ar_correo_destination_province_code = fields.Selection(selection=lambda self: self.env['delivery.carrier'].l10n_ar_get_province_codes(), string='Provincia destino Correo')
    l10n_ar_correo_agency_code = fields.Char(string='Codigo sucursal Correo')
    l10n_ar_correo_agency_name = fields.Char(string='Sucursal Correo')
    l10n_ar_correo_agency_address = fields.Char(string='Direccion sucursal Correo')
    l10n_ar_correo_product_type = fields.Char(string='Tipo producto Correo')
    l10n_ar_correo_product_name = fields.Char(string='Servicio Correo')
    l10n_ar_correo_shipping_price = fields.Float(string='Precio Correo')
    l10n_ar_correo_delivery_time_min = fields.Char(string='Plazo minimo Correo')
    l10n_ar_correo_delivery_time_max = fields.Char(string='Plazo maximo Correo')
    l10n_ar_correo_rate_valid_to = fields.Datetime(string='Cotizacion valida hasta')
    l10n_ar_correo_quote_payload = fields.Text(string='Payload cotizacion Correo')
    l10n_ar_correo_quote_response = fields.Text(string='Respuesta cotizacion Correo')
    l10n_ar_correo_shipment_ids = fields.One2many('l10n_ar.correo.shipment', 'sale_order_id', string='Envios Correo')
    l10n_ar_correo_tracking_numbers = fields.Char(string='Trackings Correo', compute='_compute_l10n_ar_correo_tracking_numbers')
    l10n_ar_correo_visible_state = fields.Char(string='Estado envio cliente', compute='_compute_l10n_ar_correo_visible_state')

    def _compute_l10n_ar_correo_tracking_numbers(self):
        for order in self:
            order.l10n_ar_correo_tracking_numbers = ', '.join(order.l10n_ar_correo_shipment_ids.mapped('tracking_number'))

    def _compute_l10n_ar_correo_visible_state(self):
        for order in self:
            shipment = order.l10n_ar_correo_shipment_ids[:1]
            order.l10n_ar_correo_visible_state = CUSTOMER_VISIBLE_STATES.get(shipment.state) if shipment else False

    def action_view_l10n_ar_correo_shipments(self):
        self.ensure_one()
        action = self.env.ref('l10n_ar_correoargentino.l10n_ar_correo_shipment_action').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        return action
