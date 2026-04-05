# -*- coding: utf-8 -*-
from odoo import api, models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _l10n_ar_afip_set_default_invoice_report(self):
        arca_report_name = 'l10n_ar_afip.report_invoice_afip_v2'

        candidates = self.search([
            ('model', '=', 'account.move'),
            ('report_type', '=', 'qweb-pdf'),
            ('report_name', 'ilike', 'account.'),
        ])

        if not candidates:
            candidates = self.search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf'),
                ('name', 'ilike', 'factura'),
            ])

        if not candidates:
            candidates = self.search([
                ('model', '=', 'account.move'),
                ('report_type', '=', 'qweb-pdf'),
                ('name', 'ilike', 'invoice'),
            ])

        if candidates:
            candidates.write({
                'report_name': arca_report_name,
                'report_file': arca_report_name,
            })

        return True
