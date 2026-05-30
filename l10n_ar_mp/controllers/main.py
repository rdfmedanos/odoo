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

    @http.route('/payment/mercado_pago/process_order', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def mercado_pago_process_order(self, **kwargs):
        import json
        try:
            data = json.loads(request.httprequest.data)
        except Exception:
            data = {}
        _logger.info('Procesando pago con tarjeta MP: %s', {k: v for k, v in data.items() if k != 'token'})

        reference = data.get('external_reference', '')
        tx = request.env['payment.transaction'].sudo().search([
            ('provider_code', '=', 'mercado_pago'),
            ('reference', '=', reference),
        ], limit=1)
        if not tx:
            return request.make_json_response({'success': False, 'error': 'Transaccion no encontrada'})

        try:
            tx._mercado_pago_process_card_payment(data)
            return request.make_json_response({
                'success': True,
                'redirect_url': '/payment/status',
            })
        except Exception as e:
            _logger.exception('Error al procesar pago MP')
            msg = str(e)
            
            error_map = {
                'rejected_by_issuer': 'La tarjeta fue rechazada por el banco emisor. Probá con otra tarjeta.',
                'invalid_card_token': 'El token de la tarjeta expiró o es inválido. Recargá la página e intentá nuevamente.',
                'insufficient_amount': 'La tarjeta no tiene fondos suficientes.',
                'call_for_auth': 'La tarjeta requiere autorización del banco emisor.',
                'call_for_authorize': 'La tarjeta requiere autorización del banco emisor.',
                'bad_filled_card_number': 'El número de la tarjeta es incorrecto.',
                'bad_filled_date': 'La fecha de vencimiento es incorrecta.',
                'bad_filled_security_code': 'El código de seguridad (CVV) es incorrecto.',
                'card_disabled': 'La tarjeta está inactiva. Comunicate con el banco emisor.',
                'duplicated_payment': 'Se detectó un pago duplicado. Intentá con otra tarjeta o esperá unos minutos.',
                'high_risk': 'El pago fue rechazado por medidas de seguridad de Mercado Pago.',
                'invalid_installments': 'La cantidad de cuotas seleccionada no está permitida para esta tarjeta.',
                'max_attempts': 'Superaste el límite de intentos permitidos. Intentá con otra tarjeta.',
            }
            
            user_msg = 'La tarjeta fue rechazada por el banco emisor. Probá con otra tarjeta.'
            matched = False
            for key, val in error_map.items():
                if key in msg:
                    user_msg = val
                    matched = True
                    break
            
            if not matched:
                if 'rejected' in msg or 'cc_rejected' in msg:
                    user_msg = 'La tarjeta fue rechazada. Probá con otra tarjeta o medio de pago.'
                else:
                    user_msg = msg
                    
            return request.make_json_response({'success': False, 'error': user_msg})

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
