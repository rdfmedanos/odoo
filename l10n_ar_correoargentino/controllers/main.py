# -*- coding: utf-8 -*-
import json
from odoo import http, _
from odoo.http import request


class CorreoArgentinoWebsiteController(http.Controller):

    @http.route('/shop/correoargentino/quote', type='json', auth='public', website=True, csrf=False)
    def quote(self, carrier_id=None, postal_code=None, province_code=None, delivery_type=None, agency_code=None, agency_name=None, agency_address=None, **kwargs):
        order = request.website.sale_get_order(force_create=True)
        if not order:
            return {'ok': False, 'error': _('No hay un carrito activo para cotizar.')}
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id)) if carrier_id else request.env['delivery.carrier'].sudo().search([('delivery_type', '=', 'l10n_ar_correoargentino')], limit=1)
        if not carrier:
            return {'ok': False, 'error': _('No hay un transportista Correo Argentino disponible.')}
        try:
            order.sudo().write({
                'carrier_id': carrier.id,
                'l10n_ar_correo_destination_postal_code': postal_code,
                'l10n_ar_correo_destination_province_code': province_code,
                'l10n_ar_correo_delivery_type': delivery_type,
                'l10n_ar_correo_agency_code': agency_code or False,
                'l10n_ar_correo_agency_name': agency_name or False,
                'l10n_ar_correo_agency_address': agency_address or False,
            })
            response = carrier._l10n_ar_fetch_rates(order.sudo(), delivery_type=delivery_type or None)
        except Exception as err:
            return {'ok': False, 'error': str(err)}
        return {'ok': True, 'rates': response.get('rates', []), 'validTo': response.get('validTo')}

    @http.route('/shop/correoargentino/select_rate', type='json', auth='public', website=True, csrf=False)
    def select_rate(self, carrier_id=None, rate=None, **kwargs):
        order = request.website.sale_get_order(force_create=True)
        if not order:
            return {'ok': False, 'error': _('No hay un carrito activo.')}
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id)) if carrier_id else order.carrier_id
        if not carrier:
            return {'ok': False, 'error': _('No se encontro el transportista para aplicar la tarifa.')}
        try:
            parsed_rate = rate if isinstance(rate, dict) else json.loads(rate or '{}')
            carrier._l10n_ar_apply_rate_to_order(order.sudo(), parsed_rate)
        except Exception as err:
            return {'ok': False, 'error': str(err)}
        return {
            'ok': True,
            'amount_total': order.amount_total,
            'shipping_price': order.l10n_ar_correo_shipping_price,
            'service_name': order.l10n_ar_correo_product_name,
        }

    @http.route('/shop/correoargentino/agencies', type='json', auth='public', website=True, csrf=False)
    def agencies(self, carrier_id=None, province_code=None, **kwargs):
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id)) if carrier_id else request.env['delivery.carrier'].sudo().search([('delivery_type', '=', 'l10n_ar_correoargentino')], limit=1)
        if not carrier:
            return {'ok': False, 'error': _('No se encontro transportista Correo Argentino.')}
        if not province_code:
            return {'ok': False, 'error': _('Debe indicar la provincia para consultar sucursales.')}
        try:
            token = carrier._l10n_ar_get_micorreo_token()
            agencies = carrier._l10n_ar_get_micorreo_api().get_agencies(token, carrier.l10n_ar_micorreo_customer_id, province_code)
        except Exception as err:
            return {'ok': False, 'error': str(err)}
        simplified = []
        for agency in agencies:
            address = agency.get('location', {}).get('address', {})
            simplified.append({
                'code': agency.get('code'),
                'name': agency.get('name'),
                'address': ', '.join(filter(None, [address.get('streetName'), address.get('streetNumber'), address.get('city')])),
            })
        return {'ok': True, 'agencies': simplified}
