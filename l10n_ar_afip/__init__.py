# -*- coding: utf-8 -*-

from . import models
from . import services
from . import reports


def _create_report_action(cr, registry):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    existing = env['ir.actions.report'].search([
        ('report_name', '=', 'l10n_ar_afip.report_invoice_afip'),
    ])
    if not existing:
        env['ir.actions.report'].create({
            'name': 'Factura ARCA (PDF)',
            'model': 'account.move',
            'report_type': 'qweb-pdf',
            'report_name': 'l10n_ar_afip.report_invoice_afip',
            'print_report_name': "'Factura_ARCA_%s' % (object.name or 'draft').replace('/', '_')",
        })
