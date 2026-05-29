# -*- coding: utf-8 -*-

import logging
import uuid
from urllib.parse import urljoin

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    l10n_ar_mp_client_id = fields.Char(
        string='Client ID',
        groups='base.group_system',
    )
    l10n_ar_mp_client_secret = fields.Char(
        string='Client Secret',
        groups='base.group_system',
    )
    l10n_ar_mp_public_key = fields.Char(
        string='Public Key',
        groups='base.group_system',
        help='Clave publica de Mercado Pago (empieza con TEST- o APP_USR-).'
    )
    l10n_ar_mp_webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_l10n_ar_mp_webhook_url',
    )

    @api.depends('code')
    def _compute_l10n_ar_mp_webhook_url(self):
        base_url = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        webhook_url = '%s/payment/mercado_pago/webhook' % (base_url or '')
        for provider in self:
            provider.l10n_ar_mp_webhook_url = webhook_url if provider.code == 'mercado_pago' else False

    def _compute_feature_support_fields(self):
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'mercado_pago').update({
            'support_tokenization': False,
            'support_manual_capture': None,
            'support_refund': 'none',
        })

    def _get_default_payment_method_codes(self):
        self.ensure_one()
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'mercado_pago':
            return default_codes
        return set(default_codes) | {'card'}

    def _get_redirect_form_view(self, is_validation=False):
        self.ensure_one()
        if self.code != 'mercado_pago':
            return super()._get_redirect_form_view(is_validation=is_validation)
        return self.env.ref('l10n_ar_mp.redirect_form')

    def _get_specific_inline_form_values(self, *args, **kwargs):
        self.ensure_one()
        if self.code != 'mercado_pago':
            return super()._get_specific_inline_form_values(*args, **kwargs)
        pk = self.l10n_ar_mp_public_key or self.mercado_pago_public_key or ''
        return {
            'public_key': pk,
            'email': '',
        }

    def write(self, values):
        card_method = self.env.ref('payment.payment_method_card', raise_if_not_found=False)
        if (
            card_method
            and 'payment_method_ids' not in values
            and self
            and all(provider.code == 'mercado_pago' for provider in self)
        ):
            values = dict(values, payment_method_ids=[(4, card_method.id)])

        result = super().write(values)
        return result

    @api.constrains('state', 'mercado_pago_access_token')
    def _check_mercado_pago_credentials_are_set_before_enabling(self):
        for provider in self.filtered(lambda p: p.code == 'mercado_pago' and p.state != 'disabled'):
            if not provider.mercado_pago_access_token:
                raise ValidationError(_('Configure el Access Token de Mercado Pago antes de habilitar el proveedor.'))

    def _mercado_pago_get_api_url(self, endpoint):
        self.ensure_one()
        return 'https://api.mercadopago.com/%s' % endpoint.lstrip('/')

    def _mercado_pago_get_headers(self, idempotency_key=None):
        self.ensure_one()
        if not self.mercado_pago_access_token:
            raise ValidationError(_('Configure el Access Token de Mercado Pago antes de operar.'))

        headers = {
            'Authorization': 'Bearer %s' % self.mercado_pago_access_token,
            'Content-Type': 'application/json',
        }
        if idempotency_key:
            headers['X-Idempotency-Key'] = idempotency_key
        return headers

    def _mercado_pago_request(self, method, endpoint, payload=None, idempotency_key=None):
        self.ensure_one()
        url = self._mercado_pago_get_api_url(endpoint)
        try:
            response = requests.request(
                method,
                url,
                json=payload,
                headers=self._mercado_pago_get_headers(idempotency_key=idempotency_key),
                timeout=30,
            )
        except requests.exceptions.RequestException as error:
            _logger.exception('Error en llamada a Mercado Pago: %s', error)
            raise ValidationError(_('Mercado Pago no respondio correctamente: %s') % error) from error

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except ValueError:
                error_data = {'message': response.text or response.reason}
            message = error_data.get('message') or error_data.get('error') or response.reason
            details = error_data.get('cause') or error_data.get('errors') or error_data.get('details')
            if details:
                message = '%s - %s' % (message, details)
            _logger.error('Mercado Pago rechazo la llamada %s %s: %s', method, url, error_data)
            raise ValidationError(_('Mercado Pago no respondio correctamente: %s') % message)

        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError as error:
            raise ValidationError(_('Mercado Pago devolvio una respuesta invalida.')) from error

    def action_l10n_ar_mp_test_connection(self):
        self.ensure_one()
        if self.code != 'mercado_pago':
            return False

        user_data = self._mercado_pago_request('GET', '/users/me')
        account_name = user_data.get('nickname') or user_data.get('email') or user_data.get('id')
        message = _('Conexion exitosa con Mercado Pago.')
        if account_name:
            message = _('Conexion exitosa con Mercado Pago: %s') % account_name
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Mercado Pago'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    def _mercado_pago_create_order_from_card(self, transaction, card_data):
        self.ensure_one()
        amount = float(transaction.amount)
        payload = {
            'type': 'online',
            'processing_mode': 'automatic',
            'total_amount': '%.2f' % amount,
            'external_reference': transaction.reference,
            'payer': {
                'email': card_data.get('payer', {}).get('email') or transaction.partner_email or transaction.partner_id.email,
            },
            'transactions': {
                'payments': [
                    {
                        'amount': '%.2f' % amount,
                        'payment_method': {
                            'id': card_data['payment_method_id'],
                            'type': card_data['payment_type_id'],
                            'token': card_data['token'],
                            'installments': int(card_data['installments']),
                        },
                    }
                ],
            },
        }
        identification = card_data.get('payer', {}).get('identification', {})
        if identification.get('type') and identification.get('number'):
            payload['payer']['identification'] = {
                'type': identification['type'],
                'number': identification['number'],
            }
        _logger.info('Payload Orders API: %s', payload)
        idempotency_key = transaction.l10n_ar_mp_idempotency_key or str(uuid.uuid4())
        transaction.l10n_ar_mp_idempotency_key = idempotency_key
        for retry in range(3):
            try:
                result = self._mercado_pago_request('POST', '/v1/orders', payload, idempotency_key=idempotency_key)
                _logger.info('Respuesta Orders API: %s', result)
                return result
            except ValidationError as e:
                _logger.warning('Intento %d fallo: %s', retry + 1, e)
                if retry == 2:
                    raise
                idempotency_key = str(uuid.uuid4())
                transaction.l10n_ar_mp_idempotency_key = idempotency_key

    def _mercado_pago_get_order(self, order_id):
        self.ensure_one()
        return self._mercado_pago_request('GET', '/v1/orders/%s' % order_id)

    def _mercado_pago_get_payment(self, payment_id):
        self.ensure_one()
        return self._mercado_pago_request('GET', '/v1/payments/%s' % payment_id)
