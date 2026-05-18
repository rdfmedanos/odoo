# -*- coding: utf-8 -*-
import json
from odoo import http, _
from odoo.http import request


class CorreoArgentinoPortalController(http.Controller):

    def _get_customer_shipments(self):
        partner = request.env.user.partner_id.commercial_partner_id
        return request.env['l10n_ar.correo.shipment'].sudo().search([
            ('partner_id', 'child_of', partner.id),
        ], order='create_date desc')

    @http.route('/my/correo-shipments', type='http', auth='user', website=True)
    def portal_my_shipments(self, **kwargs):
        shipments = self._get_customer_shipments()
        values = {
            'page_name': 'correo_shipments',
            'shipments': shipments,
        }
        return request.render('l10n_ar_correoargentino.portal_my_shipments', values)

    @http.route('/my/correo-shipments/<int:shipment_id>', type='http', auth='user', website=True)
    def portal_shipment_detail(self, shipment_id, **kwargs):
        shipment = request.env['l10n_ar.correo.shipment'].sudo().browse(shipment_id)
        partner = request.env.user.partner_id.commercial_partner_id
        if not shipment.exists() or shipment.partner_id.commercial_partner_id != partner:
            return request.not_found()
        values = {
            'page_name': 'correo_shipment_detail',
            'shipment': shipment,
            'tracking_events': json.loads(shipment.events_json or '[]'),
        }
        return request.render('l10n_ar_correoargentino.portal_shipment_detail', values)
