# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    l10n_ar_mp_order_id = fields.Char(string='Mercado Pago Order ID', readonly=True)
    l10n_ar_mp_payment_id = fields.Char(string='Mercado Pago Payment ID', readonly=True)
    l10n_ar_mp_status = fields.Char(string='Mercado Pago Status', readonly=True)
    l10n_ar_mp_idempotency_key = fields.Char(string='Mercado Pago Idempotency Key', readonly=True, copy=False)

    def _get_specific_rendering_values(self, processing_values):
        if self.provider_code != 'mercado_pago':
            return super()._get_specific_rendering_values(processing_values)

        self.ensure_one()
        provider = self.provider_id
        public_key = provider.l10n_ar_mp_public_key or provider.mercado_pago_public_key or ''
        return {
            'api_url': '',
            'url_params': {},
            'amount': self.amount,
            'public_key': public_key,
            'reference': self.reference,
            'partner_email': self.partner_email or self.partner_id.email or '',
            'partner_name': self.partner_name or self.partner_id.name or '',
        }

    def _mercado_pago_process_card_payment(self, card_data):
        self.ensure_one()
        provider = self.provider_id
        result = provider._mercado_pago_create_order_from_card(self, card_data)
        order_status = result.get('status', '')
        self.write({
            'l10n_ar_mp_order_id': result.get('id', ''),
            'l10n_ar_mp_status': order_status,
        })
        payments = result.get('transactions', {}).get('payments', [])
        if payments:
            payment = payments[0]
            self.write({
                'l10n_ar_mp_payment_id': payment.get('id', ''),
            })
            status = payment.get('status', '')
            status_detail = payment.get('status_detail', '')
            if status == 'processed' and status_detail == 'accredited':
                self._set_done()
            elif status == 'rejected':
                self._set_error(status_detail or _('Mercado Pago rechazo la operacion.'))
            elif status in ('pending', 'in_process'):
                self._set_pending()
            else:
                _logger.info('Estado de pago MP no mapeado: %s / %s', status, status_detail)
                self._set_pending()
        return result

    @api.model
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        if provider_code != 'mercado_pago':
            return super()._get_tx_from_notification_data(provider_code, notification_data)

        reference = notification_data.get('external_reference') or notification_data.get('reference')
        order_id = notification_data.get('id') or notification_data.get('order_id')
        payment_id = notification_data.get('payment_id') or notification_data.get('data', {}).get('id')
        domain = [('provider_code', '=', 'mercado_pago')]
        if reference:
            domain.append(('reference', '=', reference))
        elif order_id:
            domain.append(('l10n_ar_mp_order_id', '=', order_id))
        elif payment_id:
            domain.append(('l10n_ar_mp_payment_id', '=', payment_id))
        else:
            raise ValidationError(_('No se pudo identificar la transaccion de Mercado Pago.'))

        tx = self.search(domain, limit=1)
        if not tx:
            raise ValidationError(_('No se encontro una transaccion para la notificacion de Mercado Pago.'))
        return tx

    def _process_notification_data(self, notification_data):
        if self.provider_code != 'mercado_pago':
            return super()._process_notification_data(notification_data)

        payment_id = notification_data.get('payment_id') or notification_data.get('data', {}).get('id')
        order_id = notification_data.get('id') or notification_data.get('order_id') or self.l10n_ar_mp_order_id
        order_data = self.provider_id._mercado_pago_get_order(order_id) if order_id else notification_data
        status = order_data.get('status') or notification_data.get('status')
        payment_id = payment_id or order_data.get('payment_id')
        if not payment_id:
            payments = order_data.get('transactions', {}).get('payments', [])
            if payments:
                payment_id = payments[0].get('id')
                status = status or payments[0].get('status')
                status_detail = payments[0].get('status_detail', '')

        self.write({
            'l10n_ar_mp_order_id': order_id,
            'l10n_ar_mp_payment_id': payment_id,
            'l10n_ar_mp_status': status,
        })

        if status in ('processed', 'paid', 'approved'):
            self._set_done()
        elif status in ('authorized',):
            self._set_authorized()
        elif status in ('pending', 'in_process'):
            self._set_pending()
        elif status in ('cancelled', 'canceled', 'expired'):
            self._set_canceled()
        elif status in ('failed', 'rejected'):
            self._set_error(_('Mercado Pago rechazo la operacion.'))
        else:
            _logger.info('Estado Mercado Pago no mapeado para %s: %s', self.reference, status)
