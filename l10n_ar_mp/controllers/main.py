# -*- coding: utf-8 -*-

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MercadoPagoController(http.Controller):

    @http.route('/payment/mercado_pago/pay', type='http', auth='public', website=True, methods=['GET'], csrf=False, save_session=False)
    def mercado_pago_pay(self, **kwargs):
        reference = kwargs.get('reference', '')
        tx = request.env['payment.transaction'].sudo().search([
            ('provider_code', '=', 'mercado_pago'),
            ('reference', '=', reference),
        ], limit=1)
        if not tx:
            return request.not_found('Transaccion no encontrada')

        provider = tx.provider_id
        public_key = provider.l10n_ar_mp_public_key or provider.mercado_pago_public_key or ''
        partner = tx.partner_id
        return request.render('l10n_ar_mp.payment_page', {
            'amount': tx.amount,
            'public_key': public_key,
            'reference': tx.reference,
            'partner_email': tx.partner_email or (partner and partner.email) or '',
            'partner_name': tx.partner_name or (partner and partner.name) or '',
        })

    @http.route('/payment/mercado_pago/process_order', type='json', auth='public', methods=['POST'], csrf=False, save_session=False)
    def mercado_pago_process_order(self, **kwargs):
        data = request.get_json_data()
        _logger.info('Procesando pago con tarjeta MP: %s', {k: v for k, v in data.items() if k != 'token'})

        reference = data.get('external_reference', '')
        tx = request.env['payment.transaction'].sudo().search([
            ('provider_code', '=', 'mercado_pago'),
            ('reference', '=', reference),
        ], limit=1)
        if not tx:
            return {'success': False, 'error': 'Transaccion no encontrada'}

        try:
            tx._mercado_pago_process_card_payment(data)
            return {
                'success': True,
                'redirect_url': '/payment/status',
            }
        except Exception as e:
            _logger.exception('Error al procesar pago MP')
            return {'success': False, 'error': str(e)}

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
