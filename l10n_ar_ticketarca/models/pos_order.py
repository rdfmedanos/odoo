# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

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
        return {
            'cae': move.cae or False,
            'cae_due_date': fields.Date.to_string(move.cae_due_date) if move.cae_due_date else False,
            'qr_image': move.afip_qr_image or False,
            'qr_data': move.afip_qr_data or False,
        }
