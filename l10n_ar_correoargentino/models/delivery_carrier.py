# -*- coding: utf-8 -*-
import json
import logging
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .constants import PROVINCE_CODES, PROVINCE_NAME_TO_CODE
from ..services.micorreo_api import MiCorreoAPI
from ..services.paqar_api import PaqArAPI

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[('l10n_ar_correoargentino', 'Correo Argentino')], ondelete={'l10n_ar_correoargentino': 'set default'})

    l10n_ar_micorreo_environment = fields.Selection([
        ('testing', 'Testing'),
        ('production', 'Produccion'),
    ], string='Ambiente MiCorreo', default='testing')
    l10n_ar_micorreo_api_username = fields.Char(string='Usuario API MiCorreo')
    l10n_ar_micorreo_api_password = fields.Char(string='Password API MiCorreo')
    l10n_ar_micorreo_customer_id = fields.Char(string='Customer ID MiCorreo')
    l10n_ar_micorreo_email = fields.Char(string='Email MiCorreo')
    l10n_ar_micorreo_password = fields.Char(string='Password MiCorreo')
    l10n_ar_micorreo_last_token = fields.Char(string='Ultimo token MiCorreo', copy=False)
    l10n_ar_micorreo_token_expires = fields.Datetime(string='Vencimiento token MiCorreo', copy=False)

    l10n_ar_paqar_environment = fields.Selection([
        ('testing', 'Testing'),
        ('production', 'Produccion'),
    ], string='Ambiente PaqAr', default='testing')
    l10n_ar_paqar_api_key = fields.Char(string='API Key PaqAr')
    l10n_ar_paqar_agreement = fields.Char(string='Agreement PaqAr')
    l10n_ar_paqar_seller_id = fields.Char(string='Seller ID PaqAr')
    l10n_ar_paqar_ext_client = fields.Char(string='Ext Client PaqAr')

    l10n_ar_origin_street_name = fields.Char(string='Calle origen')
    l10n_ar_origin_street_number = fields.Char(string='Numero origen')
    l10n_ar_origin_floor = fields.Char(string='Piso origen')
    l10n_ar_origin_apartment = fields.Char(string='Depto origen')
    l10n_ar_origin_city = fields.Char(string='Ciudad origen')
    l10n_ar_origin_province_code = fields.Selection(PROVINCE_CODES, string='Provincia origen')
    l10n_ar_origin_postal_code = fields.Char(string='Codigo postal origen')
    l10n_ar_origin_business_name = fields.Char(string='Remitente')
    l10n_ar_origin_email = fields.Char(string='Email remitente')
    l10n_ar_origin_phone = fields.Char(string='Telefono remitente')
    l10n_ar_origin_cellphone = fields.Char(string='Celular remitente')

    l10n_ar_default_weight_g = fields.Integer(string='Peso por defecto (g)', default=1000)
    l10n_ar_default_height_cm = fields.Integer(string='Alto por defecto (cm)', default=10)
    l10n_ar_default_width_cm = fields.Integer(string='Ancho por defecto (cm)', default=10)
    l10n_ar_default_length_cm = fields.Integer(string='Largo por defecto (cm)', default=10)
    l10n_ar_allow_home_delivery = fields.Boolean(string='Permitir domicilio', default=True)
    l10n_ar_allow_agency_delivery = fields.Boolean(string='Permitir sucursal', default=True)
    l10n_ar_default_product_type = fields.Char(string='Tipo de producto', default='CP')
    l10n_ar_price_margin = fields.Float(string='Recargo fijo')

    l10n_ar_shipment_ids = fields.One2many('l10n_ar.correo.shipment', 'carrier_id', string='Envios Correo Argentino')

    def _l10n_ar_get_micorreo_api(self):
        self.ensure_one()
        return MiCorreoAPI(
            self.l10n_ar_micorreo_api_username,
            self.l10n_ar_micorreo_api_password,
            self.l10n_ar_micorreo_environment,
        )

    def _l10n_ar_get_paqar_api(self):
        self.ensure_one()
        return PaqArAPI(
            self.l10n_ar_paqar_api_key,
            self.l10n_ar_paqar_agreement,
            self.l10n_ar_paqar_environment,
        )

    def _l10n_ar_get_micorreo_token(self, force=False):
        self.ensure_one()
        if not force and self.l10n_ar_micorreo_last_token and self.l10n_ar_micorreo_token_expires and self.l10n_ar_micorreo_token_expires > fields.Datetime.now():
            return self.l10n_ar_micorreo_last_token
        token_data = self._l10n_ar_get_micorreo_api().get_token()
        token = token_data.get('token')
        expires = token_data.get('expires')
        values = {'l10n_ar_micorreo_last_token': token}
        if expires:
            values['l10n_ar_micorreo_token_expires'] = fields.Datetime.to_datetime(expires)
        self.write(values)
        return token

    def _l10n_ar_get_partner_province_code(self, partner):
        state = partner.state_id
        if not state:
            return False
        candidates = [state.code or '', state.name or '']
        for candidate in candidates:
            normalized = candidate.strip()
            if not normalized:
                continue
            if len(normalized) == 1 and normalized.upper() in dict(PROVINCE_CODES):
                return normalized.upper()
            upper = normalized.upper()
            if upper.startswith('AR-') and upper[-1] in dict(PROVINCE_CODES):
                return upper[-1]
            key = normalized.lower()
            if key in PROVINCE_NAME_TO_CODE:
                return PROVINCE_NAME_TO_CODE[key]
        return False

    def _l10n_ar_get_order_destination_postal_code(self, order):
        return order.l10n_ar_correo_destination_postal_code or order.partner_shipping_id.zip or order.partner_id.zip

    def _l10n_ar_get_order_destination_province_code(self, order):
        return order.l10n_ar_correo_destination_province_code or self._l10n_ar_get_partner_province_code(order.partner_shipping_id or order.partner_id)

    def _l10n_ar_get_package_values(self, order):
        weight_g = 0
        max_length = 0
        max_width = 0
        total_height = 0
        for line in order.order_line.filtered(lambda l: not l.display_type and not l.is_delivery and l.product_id.type in ('consu', 'product')):
            qty = max(int(line.product_uom_qty), 1)
            product = line.product_id.product_tmpl_id
            line_weight = int(round((product.weight or 0.0) * 1000))
            if not line_weight:
                line_weight = self.l10n_ar_default_weight_g
            length = int(product.l10n_ar_length_cm or self.l10n_ar_default_length_cm or 0)
            width = int(product.l10n_ar_width_cm or self.l10n_ar_default_width_cm or 0)
            height = int(product.l10n_ar_height_cm or self.l10n_ar_default_height_cm or 0)
            weight_g += line_weight * qty
            max_length = max(max_length, length)
            max_width = max(max_width, width)
            total_height += height * qty
        values = {
            'weight': weight_g,
            'height': total_height,
            'width': max_width,
            'length': max_length,
        }
        if not all(values.values()):
            raise UserError(_('Faltan peso o dimensiones para cotizar el envio con Correo Argentino.'))
        if values['weight'] < 1 or values['weight'] > 25000:
            raise UserError(_('El peso total debe estar entre 1g y 25000g para cotizar en Correo Argentino.'))
        for dim_name in ('height', 'width', 'length'):
            if values[dim_name] < 1 or values[dim_name] > 150:
                raise UserError(_('Las dimensiones para cotizacion deben estar entre 1 y 150 cm.'))
        return values

    def _l10n_ar_build_rates_payload(self, order, delivery_type=None):
        self.ensure_one()
        if not self.l10n_ar_micorreo_customer_id:
            raise UserError(_('Debe configurar el Customer ID de MiCorreo en el transportista.'))
        payload = {
            'customerId': self.l10n_ar_micorreo_customer_id,
            'postalCodeOrigin': self.l10n_ar_origin_postal_code,
            'postalCodeDestination': self._l10n_ar_get_order_destination_postal_code(order),
            'dimensions': self._l10n_ar_get_package_values(order),
        }
        if not payload['postalCodeOrigin'] or not payload['postalCodeDestination']:
            raise UserError(_('Debe indicar codigo postal de origen y destino para cotizar el envio.'))
        if delivery_type:
            payload['deliveredType'] = delivery_type
        return payload

    def _l10n_ar_fetch_rates(self, order, delivery_type=None):
        self.ensure_one()
        token = self._l10n_ar_get_micorreo_token()
        payload = self._l10n_ar_build_rates_payload(order, delivery_type=delivery_type)
        response = self._l10n_ar_get_micorreo_api().get_rates(token, payload)
        order.write({
            'l10n_ar_correo_quote_payload': json.dumps(payload, indent=2, ensure_ascii=True),
            'l10n_ar_correo_quote_response': json.dumps(response, indent=2, ensure_ascii=True),
            'l10n_ar_correo_rate_valid_to': response.get('validTo'),
        })
        return response

    def _l10n_ar_apply_rate_to_order(self, order, rate):
        self.ensure_one()
        price = float(rate.get('price', 0.0)) + self.l10n_ar_price_margin
        if hasattr(order, 'set_delivery_line'):
            order.set_delivery_line(self, price)
        order.write({
            'carrier_id': self.id,
            'l10n_ar_correo_delivery_type': rate.get('deliveredType'),
            'l10n_ar_correo_product_type': rate.get('productType'),
            'l10n_ar_correo_product_name': rate.get('productName'),
            'l10n_ar_correo_shipping_price': price,
            'l10n_ar_correo_delivery_time_min': rate.get('deliveryTimeMin'),
            'l10n_ar_correo_delivery_time_max': rate.get('deliveryTimeMax'),
        })
        return price

    def rate_shipment(self, order):
        self.ensure_one()
        response = self._l10n_ar_fetch_rates(order, delivery_type=order.l10n_ar_correo_delivery_type or None)
        rates = response.get('rates') or []
        delivery_type = order.l10n_ar_correo_delivery_type
        if delivery_type:
            rates = [rate for rate in rates if rate.get('deliveredType') == delivery_type]
        if not rates:
            return {'success': False, 'price': 0.0, 'error_message': _('Correo Argentino no devolvio tarifas para este pedido.')}
        selected_rate = rates[0]
        price = float(selected_rate.get('price', 0.0)) + self.l10n_ar_price_margin
        return {
            'success': True,
            'price': price,
            'warning_message': False,
            'error_message': False,
        }

    def l10n_ar_action_test_micorreo(self):
        for carrier in self:
            token = carrier._l10n_ar_get_micorreo_token(force=True)
            if not token:
                raise UserError(_('No se pudo obtener token de MiCorreo.'))
        return self._display_notification(_('MiCorreo autenticado correctamente.'))

    def l10n_ar_action_validate_micorreo_user(self):
        self.ensure_one()
        if not self.l10n_ar_micorreo_email or not self.l10n_ar_micorreo_password:
            raise UserError(_('Debe completar email y password MiCorreo para validar el usuario.'))
        token = self._l10n_ar_get_micorreo_token(force=True)
        response = self._l10n_ar_get_micorreo_api().validate_user(token, self.l10n_ar_micorreo_email, self.l10n_ar_micorreo_password)
        customer_id = response.get('customerId')
        if not customer_id:
            raise UserError(_('MiCorreo no devolvio customerId para el usuario validado.'))
        self.write({'l10n_ar_micorreo_customer_id': customer_id})
        return self._display_notification(_('Customer ID MiCorreo actualizado: %s') % customer_id)

    def l10n_ar_action_test_paqar(self):
        for carrier in self:
            carrier._l10n_ar_get_paqar_api().auth()
        return self._display_notification(_('PaqAr autenticado correctamente.'))

    def _display_notification(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Correo Argentino'),
                'message': message,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def l10n_ar_get_province_codes(self):
        return PROVINCE_CODES
