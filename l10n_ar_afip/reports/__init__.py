# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _name = 'l10n_ar_afip.report'
    _description = 'Reporte Factura Argentina'

    def _get_report_values(self, docids, data=None):
        docs = self.env['account.move'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': docs,
        }
