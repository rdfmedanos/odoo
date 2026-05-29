# -*- coding: utf-8 -*-

import logging

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    @http.route('/payment/mercado_pago/return', type='http', auth='public', methods=['GET', 'POST'], csrf=False, save_session=False)
    def mercado_pago_return(self, **data):
        _logger.info('Retorno Mercado Pago recibido: %s', data)
        request.env['payment.transaction'].sudo()._handle_notification_data('mercado_pago', data)
        return request.redirect('/payment/status')

    @http.route('/payment/mercado_pago/webhook', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def mercado_pago_webhook(self, **data):
        payload = request.get_json_data(silent=True) or data
        if payload.get('data', {}).get('id') and not payload.get('payment_id'):
            payload['payment_id'] = payload['data']['id']
        if payload.get('resource') and not payload.get('payment_id'):
            payload['payment_id'] = payload['resource'].rstrip('/').split('/')[-1]
        _logger.info('Webhook Mercado Pago recibido: %s', payload)
        request.env['payment.transaction'].sudo()._handle_notification_data('mercado_pago', payload)
        return request.make_json_response({'status': 'ok'})
