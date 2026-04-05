# -*- coding: utf-8 -*-
from odoo import models


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _render_qweb_pdf(self, report_ref, docids, data, attachment=None, engine='qweb', check_main=True):
        return super()._render_qweb_pdf(report_ref, docids, data, attachment, engine, check_main)
