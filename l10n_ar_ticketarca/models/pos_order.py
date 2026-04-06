# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _generate_pos_order_invoice(self):
        invoice = super()._generate_pos_order_invoice()
        for order in self:
            move = order.account_move or invoice
            if not move or move.cae:
                continue
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            if not move.company_id.afip_ws_environment or not move.l10n_ar_afip_available:
                continue
            try:
                move.afip_document_type = move._get_afip_document_type()
                move.action_request_afip_cae()
            except Exception:
                _logger.exception("No se pudo autorizar ARCA automaticamente para POS %s", order.name)
        return invoice

    @api.model
    def _l10n_ar_ticketarca_fmt_amount(self, amount):
        amount = amount or 0.0
        return ('%.2f' % amount).replace('.', ',')

    l10n_ar_afip_cae = fields.Char(
        related='account_move.cae',
        readonly=True,
        string='CAE',
    )
    l10n_ar_afip_cae_due_date = fields.Date(
        related='account_move.cae_due_date',
        readonly=True,
        string='Vencimiento CAE',
    )
    l10n_ar_afip_qr_image = fields.Binary(
        related='account_move.afip_qr_image',
        readonly=True,
        string='QR AFIP',
    )
    l10n_ar_afip_qr_data = fields.Char(
        related='account_move.afip_qr_data',
        readonly=True,
        string='Datos QR AFIP',
    )

    @api.model
    def l10n_ar_get_ticket_afip_data(self, order_id):
        order = self.browse(order_id).exists()
        return order._l10n_ar_build_ticket_afip_data()

    @api.model
    def l10n_ar_get_ticket_afip_data_by_uuid(self, order_uuid):
        order = self.search([('uuid', '=', order_uuid)], limit=1)
        return order._l10n_ar_build_ticket_afip_data()

    def _l10n_ar_build_ticket_afip_data(self):
        self.ensure_one()
        order = self
        if not order or not order.account_move:
            return {}

        move = order.account_move
        if (
            not move.cae
            and move.state == 'posted'
            and move.move_type in ('out_invoice', 'out_refund')
            and move.company_id.afip_ws_environment
            and move.l10n_ar_afip_available
        ):
            try:
                move.afip_document_type = move._get_afip_document_type()
                move.action_request_afip_cae()
            except Exception:
                _logger.exception("No se pudo obtener CAE al preparar ticket POS %s", order.name)

        company = order.company_id
        partner = order.partner_id
        invoice_date = move.invoice_date or order.date_order.date()

        company_address = ', '.join([
            part for part in [company.street, company.city, company.state_id.name if company.state_id else False] if part
        ])
        partner_address = ', '.join([
            part for part in [partner.street, partner.city, partner.state_id.name if partner.state_id else False] if part
        ]) if partner else False

        amount_untaxed = order.amount_total - order.amount_tax
        amount_tax = order.amount_tax
        amount_total = order.amount_total
        amount_paid = order.amount_paid
        amount_change = order.amount_return

        return {
            'cae': move.cae or False,
            'cae_due_date': fields.Date.to_string(move.cae_due_date) if move.cae_due_date else False,
            'qr_image': move.afip_qr_image or False,
            'qr_data': move.afip_qr_data or False,
            'barcode': move.afip_barcode or False,
            'invoice_number': move.afip_document_number or move.name or False,
            'invoice_letter': move.afip_document_type or False,
            'invoice_date': fields.Date.to_string(invoice_date) if invoice_date else False,
            'company_name': company.name or False,
            'company_cuit': company.afip_cuit or company.vat or False,
            'company_iibb': company.l10n_ar_afip_iibb or False,
            'company_start_date': fields.Date.to_string(company.l10n_ar_afip_start_date) if company.l10n_ar_afip_start_date else False,
            'company_iva': company.l10n_ar_afip_responsibility_type_id.name if company.l10n_ar_afip_responsibility_type_id else False,
            'company_address': company_address or False,
            'company_phone': company.phone or False,
            'partner_name': partner.name if partner else False,
            'partner_vat': partner.vat if partner else False,
            'partner_iva': partner.l10n_ar_afip_responsibility_type_id.name if partner and partner.l10n_ar_afip_responsibility_type_id else False,
            'partner_address': partner_address,
            'partner_email': partner.email if partner else False,
            'partner_phone': partner.phone if partner else False,
            'order_name': order.name or False,
            'amount_untaxed': self._l10n_ar_ticketarca_fmt_amount(amount_untaxed),
            'amount_tax': self._l10n_ar_ticketarca_fmt_amount(amount_tax),
            'amount_total': self._l10n_ar_ticketarca_fmt_amount(amount_total),
            'amount_paid': self._l10n_ar_ticketarca_fmt_amount(amount_paid),
            'amount_change': self._l10n_ar_ticketarca_fmt_amount(amount_change),
        }
