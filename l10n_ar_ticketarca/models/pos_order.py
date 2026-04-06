# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

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
        if not order or not order.account_move:
            return {}

        move = order.account_move
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
