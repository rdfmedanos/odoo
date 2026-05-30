# -*- coding: utf-8 -*-
import logging
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    andreani_username = fields.Char(string='Usuario API Andreani')
    andreani_password = fields.Char(string='Contraseña API Andreani')
    andreani_client_number = fields.Char(string='Número de Cliente')
    andreani_contract_number = fields.Char(string='Número de Contrato')
    andreani_env = fields.Selection([
        ('test', 'Pruebas'),
        ('prod', 'Producción'),
    ], string='Entorno', default='test')
    andreani_volumetric_divisor = fields.Integer(
        string='Divisor volumétrico',
        default=5000,
        help='Usado para calcular peso volumétrico: (largo × ancho × alto) / divisor',
    )

    def get_values(self):
        res = super().get_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        res.update(
            andreani_username=IrConfig.get_param('delivery_andreani.username', default=''),
            andreani_password=IrConfig.get_param('delivery_andreani.password', default=''),
            andreani_client_number=IrConfig.get_param('delivery_andreani.client_number', default=''),
            andreani_contract_number=IrConfig.get_param('delivery_andreani.contract_number', default=''),
            andreani_env=IrConfig.get_param('delivery_andreani.env', default='test'),
            andreani_volumetric_divisor=int(IrConfig.get_param('delivery_andreani.volumetric_divisor', default=5000)),
        )
        return res

    def set_values(self):
        super().set_values()
        IrConfig = self.env['ir.config_parameter'].sudo()
        IrConfig.set_param('delivery_andreani.username', self.andreani_username or '')
        IrConfig.set_param('delivery_andreani.password', self.andreani_password or '')
        IrConfig.set_param('delivery_andreani.client_number', self.andreani_client_number or '')
        IrConfig.set_param('delivery_andreani.contract_number', self.andreani_contract_number or '')
        IrConfig.set_param('delivery_andreani.env', self.andreani_env or 'test')
        IrConfig.set_param('delivery_andreani.volumetric_divisor', str(self.andreani_volumetric_divisor or 5000))

    def action_test_andreani_credentials(self):
        username = self.andreani_username
        password = self.andreani_password
        env = self.andreani_env

        if not username or not password:
            raise UserError(_('Faltan Usuario/Contraseña de Andreani para realizar la prueba.'))

        base_url = 'https://apisqa.andreani.com' if env == 'test' else 'https://apis.andreani.com'
        try:
            resp = requests.post(
                f'{base_url}/login',
                auth=(username, password),
                timeout=20,
            )
        except requests.exceptions.RequestException as e:
            raise UserError(_('Error conectando con Andreani: %s') % str(e))

        if resp.status_code in (200, 204):
            token = resp.headers.get('x-authorization-token')
            if not token:
                try:
                    token = resp.json().get('token')
                except Exception:
                    pass
            if token:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Andreani'),
                        'type': 'success',
                        'message': _('Conexión OK. Token obtenido correctamente.'),
                        'sticky': False,
                    },
                }
            raise UserError(
                _('Respuesta válida pero no se encontró token en headers ni body. Código HTTP: %s') % resp.status_code)
        else:
            try:
                msg = resp.json().get('message', '')
            except Exception:
                msg = resp.text[:200]
            raise UserError(
                _('Error probando credenciales de Andreani (HTTP %s): %s') % (resp.status_code, msg))
