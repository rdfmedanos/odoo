# -*- coding: utf-8 -*-

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_config(self):
        params = super()._loader_params_pos_config()
        fields = params.setdefault('search_params', {}).setdefault('fields', [])
        if 'l10n_ar_ticketarca_paper_width' not in fields:
            fields.append('l10n_ar_ticketarca_paper_width')
        return params
