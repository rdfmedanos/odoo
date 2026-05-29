# -*- coding: utf-8 -*-

import logging
import uuid

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
    l10n_ar_mp_webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_l10n_ar_mp_webhook_url',
    )

    @api.depends('code')
    def _compute_l10n_ar_mp_webhook_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        webhook_url = '%s/payment/mercado_pago/webhook' % (base_url or '')
        for provider in self:
            provider.l10n_ar_mp_webhook_url = webhook_url if provider.code == 'mercado_pago' else False

    def _compute_mercado_pago_is_oauth_supported(self):
        for provider in self:
            provider.mercado_pago_is_oauth_supported = False

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
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            _logger.exception('Error en llamada a Mercado Pago: %s', error)
            raise ValidationError(_('Mercado Pago no respondio correctamente: %s') % error) from error

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

    def _mercado_pago_create_order(self, transaction):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        currency = transaction.currency_id.name
        amount = float(transaction.amount)
        payload = {
            'type': 'online',
            'external_reference': transaction.reference,
            'total_amount': str(amount),
            'transactions': {
                'payments': [
                    {
                        'amount': str(amount),
                        'payment_method': {
                            'id': 'account_money',
                            'type': 'wallet',
                        },
                    }
                ],
            },
            'payer': {
                'email': transaction.partner_email or transaction.partner_id.email,
            },
            'back_urls': {
                'success': '%s/payment/mercado_pago/return' % base_url,
                'pending': '%s/payment/mercado_pago/return' % base_url,
                'failure': '%s/payment/mercado_pago/return' % base_url,
            },
            'notification_url': '%s/payment/mercado_pago/webhook' % base_url,
            'description': transaction.reference,
            'currency': currency,
        }
        idempotency_key = transaction.l10n_ar_mp_idempotency_key or str(uuid.uuid4())
        transaction.l10n_ar_mp_idempotency_key = idempotency_key
        return self._mercado_pago_request('POST', '/v1/orders', payload, idempotency_key=idempotency_key)

    def _mercado_pago_get_order(self, order_id):
        self.ensure_one()
        return self._mercado_pago_request('GET', '/v1/orders/%s' % order_id)
