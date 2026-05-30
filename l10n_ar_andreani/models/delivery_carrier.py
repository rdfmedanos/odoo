# -*- coding: utf-8 -*-
import logging
import base64
import requests
from datetime import timedelta
from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('andreani', 'Andreani')],
        ondelete={'andreani': 'set default'},
    )

    andreani_username = fields.Char(string='Usuario API Andreani')
    andreani_password = fields.Char(string='Contraseña API Andreani')
    andreani_client_number = fields.Char(string='Número de Cliente')
    andreani_contract_number = fields.Char(string='Número de Contrato')
    andreani_env = fields.Selection([
        ('test', 'Pruebas'),
        ('prod', 'Producción'),
    ], string='Entorno', default='test')
    andreani_token = fields.Char(string='Token Andreani', copy=False)
    andreani_token_expires = fields.Datetime(string='Token expira', copy=False)
    andreani_volumetric_divisor = fields.Integer(
        string='Divisor volumétrico',
        default=5000,
        help='Usado para calcular peso volumétrico: (largo × ancho × alto) / divisor',
    )
    andreani_origin_zip = fields.Char(string='Código Postal Origen')
    andreani_default_weight_g = fields.Integer(string='Peso por defecto (g)', default=500)
    andreani_default_length_cm = fields.Integer(string='Largo por defecto (cm)', default=10)
    andreani_default_width_cm = fields.Integer(string='Ancho por defecto (cm)', default=10)
    andreani_default_height_cm = fields.Integer(string='Alto por defecto (cm)', default=10)

    def _andreani_base_url(self):
        self.ensure_one()
        if self.andreani_env == 'prod':
            return 'https://apis.andreani.com'
        return 'https://apisqa.andreani.com'

    def _andreani_get_credentials(self):
        self.ensure_one()
        username = self.andreani_username
        password = self.andreani_password
        client = self.andreani_client_number
        contract = self.andreani_contract_number
        env = self.andreani_env
        divisor = self.andreani_volumetric_divisor

        if not username or not password:
            company = self.env.company
            username = username or company.andreani_username
            password = password or company.andreani_password
            client = client or company.andreani_client_number
            contract = contract or company.andreani_contract_number
            env = env or company.andreani_env or 'test'
            divisor = divisor or company.andreani_volumetric_divisor or 5000

        return {
            'username': username,
            'password': password,
            'client_number': client,
            'contract_number': contract,
            'env': env,
            'volumetric_divisor': divisor,
        }

    def _andreani_get_token(self, force=False):
        self.ensure_one()
        creds = self._andreani_get_credentials()
        if not creds['username'] or not creds['password']:
            raise UserError(_('Debe configurar las credenciales de Andreani en el transportista o en Ajustes.'))

        margin = fields.Datetime.now()
        if not force and self.andreani_token and self.andreani_token_expires and self.andreani_token_expires > margin:
            return self.andreani_token

        base_url = self._andreani_base_url()
        try:
            resp = requests.post(
                f'{base_url}/login',
                auth=(creds['username'], creds['password']),
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            raise UserError(_('Error de conexión con Andreani: %s') % str(e))

        if resp.status_code not in (200, 204):
            try:
                msg = resp.json().get('message', '')
            except Exception:
                msg = resp.text[:200]
            raise UserError(_('Error de autenticación Andreani (HTTP %s): %s') % (resp.status_code, msg))

        token = resp.headers.get('x-authorization-token')
        if not token:
            try:
                token = resp.json().get('token')
            except Exception:
                pass
        if not token:
            raise UserError(_('Andreani no devolvió un token en la respuesta.'))

        expires = fields.Datetime.now() + timedelta(hours=23, minutes=50)
        self.write({
            'andreani_token': token,
            'andreani_token_expires': expires,
        })
        return token

    def _andreani_request(self, method, path, **kwargs):
        self.ensure_one()
        token = self._andreani_get_token()
        base_url = self._andreani_base_url()
        url = f'{base_url}{path}'
        headers = kwargs.pop('headers', {})
        headers['x-authorization-token'] = token
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 30

        try:
            resp = requests.request(method, url, headers=headers, **kwargs)
        except requests.exceptions.RequestException as e:
            raise UserError(_('Error de conexión con Andreani: %s') % str(e))

        if resp.status_code == 401:
            _logger.info('Token Andreani expirado, renovando...')
            self.write({'andreani_token': False, 'andreani_token_expires': False})
            token = self._andreani_get_token(force=True)
            headers['x-authorization-token'] = token
            try:
                resp = requests.request(method, url, headers=headers, **kwargs)
            except requests.exceptions.RequestException as e:
                raise UserError(_('Error de conexión con Andreani: %s') % str(e))

        return resp

    def _andreani_get_source_zip(self):
        self.ensure_one()
        zip_code = self.andreani_origin_zip or self.env.company.zip or ''
        return zip_code.strip()

    def _andreani_get_package_data(self, order):
        weight_g = 0
        max_length = 0
        max_width = 0
        total_height = 0
        for line in order.order_line.filtered(lambda l: not l.display_type and not l.is_delivery and l.product_id.type in ('consu', 'product')):
            qty = max(int(line.product_uom_qty), 1)
            product = line.product_id
            line_weight = int(round((product.weight or 0.0) * 1000))
            if not line_weight:
                line_weight = self.andreani_default_weight_g or 500
            length = int(product.product_tmpl_id.andreani_length_cm or self.andreani_default_length_cm or 10)
            width = int(product.product_tmpl_id.andreani_width_cm or self.andreani_default_width_cm or 10)
            height = int(product.product_tmpl_id.andreani_height_cm or self.andreani_default_height_cm or 10)
            weight_g += line_weight * qty
            max_length = max(max_length, length)
            max_width = max(max_width, width)
            total_height += height * qty
        return {
            'weight': weight_g or self.andreani_default_weight_g or 500,
            'height': total_height or self.andreani_default_height_cm or 10,
            'width': max_width or self.andreani_default_width_cm or 10,
            'length': max_length or self.andreani_default_length_cm or 10,
        }

    def _andreani_get_picking_package_data(self, picking):
        weight_g = 0
        max_length = 0
        max_width = 0
        total_height = 0
        for move in picking.move_ids:
            product = move.product_id
            if not product or product.type not in ('consu', 'product'):
                continue
            qty = int(move.product_uom_qty or move.quantity_done or 0)
            if not qty:
                continue
            line_weight = int(round((product.weight or 0.0) * 1000))
            if not line_weight:
                line_weight = self.andreani_default_weight_g or 500
            length = int(product.product_tmpl_id.andreani_length_cm or self.andreani_default_length_cm or 10)
            width = int(product.product_tmpl_id.andreani_width_cm or self.andreani_default_width_cm or 10)
            height = int(product.product_tmpl_id.andreani_height_cm or self.andreani_default_height_cm or 10)
            weight_g += line_weight * qty
            max_length = max(max_length, length)
            max_width = max(max_width, width)
            total_height += height * qty
        return {
            'weight': weight_g or self.andreani_default_weight_g or 500,
            'height': total_height or self.andreani_default_height_cm or 10,
            'width': max_width or self.andreani_default_width_cm or 10,
            'length': max_length or self.andreani_default_length_cm or 10,
        }

    def _andreani_compute_volumetric_weight(self, package):
        vol = package['length'] * package['width'] * package['height']
        divisor = self.andreani_volumetric_divisor or 5000
        return vol / divisor

    def _andreani_get_rate_configuration_error(self):
        self.ensure_one()
        creds = self._andreani_get_credentials()
        if not creds['username'] or not creds['password']:
            return _('Faltan credenciales de Andreani.')
        if not creds['client_number']:
            return _('Falta número de cliente Andreani.')
        if not creds['contract_number']:
            return _('Falta número de contrato Andreani.')
        return False

    def _is_available_for_order(self, order):
        self.ensure_one()
        if self.delivery_type == 'andreani' and self._andreani_get_rate_configuration_error():
            return False
        return super()._is_available_for_order(order)

    def andreani_rate_shipment(self, order):
        self.ensure_one()
        config_error = self._andreani_get_rate_configuration_error()
        if config_error:
            return {
                'success': False,
                'price': 0.0,
                'warning_message': False,
                'error_message': _('Andreani: %s') % config_error,
            }

        try:
            package = self._andreani_get_package_data(order)
            dest_zip = (order.partner_shipping_id.zip or order.partner_id.zip or '').strip()
            source_zip = self._andreani_get_source_zip()
            if not dest_zip:
                return {'success': False, 'price': 0.0, 'error_message': _('Falta código postal de destino.'), 'warning_message': False}
            if not source_zip:
                return {'success': False, 'price': 0.0, 'error_message': _('Falta código postal de origen.'), 'warning_message': False}

            weight_kg = package['weight'] / 1000.0
            vol = package['length'] * package['width'] * package['height']
            volume_m3 = vol / 1000000.0
            volumetric_kg = self._andreani_compute_volumetric_weight(package)
            final_weight = max(weight_kg, volumetric_kg)

            params = {
                'peso_total': final_weight,
                'volumen_total': volume_m3,
                'cp_origen': source_zip,
                'cp_destino': dest_zip,
            }
            resp = self._andreani_request('GET', '/v1/tarifas', params=params)
        except UserError:
            raise
        except Exception as err:
            _logger.exception('Error cotizando Andreani para %s', order.name)
            return {'success': False, 'price': 0.0, 'error_message': _('Error al cotizar: %s') % str(err), 'warning_message': False}

        if resp.status_code != 200:
            return {'success': False, 'price': 0.0, 'error_message': _('Andreani devolvió HTTP %s') % resp.status_code, 'warning_message': False}

        try:
            data = resp.json()
        except Exception:
            return {'success': False, 'price': 0.0, 'error_message': _('Respuesta inválida de Andreani.'), 'warning_message': False}

        price = float(data.get('tarifa', data.get('precio', data.get('price', 0.0))))
        if not price:
            return {'success': False, 'price': 0.0, 'error_message': _('Andreani no devolvió tarifa.'), 'warning_message': False}

        return {'success': True, 'price': price, 'warning_message': False, 'error_message': False}

    def andreani_send_shipping(self, pickings):
        self.ensure_one()
        creds = self._andreani_get_credentials()
        config_error = self._andreani_get_rate_configuration_error()
        if config_error:
            raise UserError(_('Andreani: %s') % config_error)

        result = []
        for picking in pickings:
            sale_order = picking.sale_id
            partner = picking.partner_id
            source_zip = self._andreani_get_source_zip()
            dest_zip = (partner.zip or '').strip()

            if not dest_zip:
                raise UserError(_('Falta código postal de destino en el picking %s.') % picking.name)

            package_data = self._andreani_get_package_data(sale_order) if sale_order else self._andreani_get_picking_package_data(picking)
            bultos = [{
                'orden': 1,
                'peso': package_data['weight'] / 1000.0,
                'largo': package_data['length'],
                'ancho': package_data['width'],
                'alto': package_data['height'],
                'contenido': _('Productos'),
            }]

            company = self.env.company
            remitente = {
                'nombre': company.name or ' ',
                'calle': company.street or ' ',
                'numero': company.street_number or 'S/N',
                'localidad': company.city or ' ',
                'provincia': company.state_id.name or ' ',
                'codigoPostal': source_zip,
                'email': company.email or ' ',
                'telefono': company.phone or ' ',
            }

            destinatario = {
                'nombre': partner.name or ' ',
                'calle': partner.street or ' ',
                'numero': partner.street_number or 'S/N',
                'localidad': partner.city or ' ',
                'provincia': partner.state_id.name or ' ',
                'codigoPostal': dest_zip,
                'email': partner.email or ' ',
                'telefono': partner.phone or ' ',
            }

            referencias = [{'tipo': 'remito', 'valor': picking.name}]
            if sale_order:
                referencias.append({'tipo': 'pedido', 'valor': sale_order.name})

            payload = {
                'numeroCliente': creds['client_number'],
                'numeroContrato': creds['contract_number'],
                'remitente': remitente,
                'destinatario': destinatario,
                'bultos': bultos,
                'referencias': referencias,
            }

            try:
                resp = self._andreani_request('POST', '/v2/ordenes-de-envio', json=payload)
            except Exception as err:
                raise UserError(_('Error al crear envío Andreani en %s: %s') % (picking.name, str(err)))

            if resp.status_code not in (200, 201):
                try:
                    msg = resp.json().get('message', resp.text[:300])
                except Exception:
                    msg = resp.text[:300]
                raise UserError(_('Andreani rechazó el envío %s (HTTP %s): %s') % (picking.name, resp.status_code, msg))

            try:
                data = resp.json()
            except Exception:
                raise UserError(_('Respuesta inválida de Andreani al crear envío %s.') % picking.name)

            numero_andreani = data.get('numeroAndreani')
            if not numero_andreani:
                numero_andreani = data.get('numeroDeEnvio')
            if not numero_andreani:
                raise UserError(_('Andreani no devolvió número de seguimiento para %s.') % picking.name)

            try:
                label_resp = self._andreani_request(
                    'GET', f'/v2/ordenes-de-envio/{numero_andreani}/etiquetas')
            except Exception:
                _logger.warning('No se pudo descargar etiqueta para %s', numero_andreani)
                label_resp = None

            if label_resp and label_resp.status_code == 200:
                pdf_bytes = label_resp.content
                filename = f'Andreani_{numero_andreani}.pdf'
                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_bytes),
                    'res_model': 'stock.picking',
                    'res_id': picking.id,
                    'mimetype': 'application/pdf',
                })
                picking.message_post(
                    body=_('Etiqueta Andreani <a href=#id=%(id)s&model=ir.attachment>%(name)s</a> generada.') % {
                        'id': attachment.id,
                        'name': filename,
                    },
                    attachment_ids=[attachment.id],
                )

            picking.write({'carrier_tracking_ref': numero_andreani})

            price = float(data.get('tarifa', data.get('precio', 0.0)))
            result.append({
                'tracking_number': numero_andreani,
                'exact_price': price,
            })

        return result

    def get_tracking_link(self, tracking_number):
        if not tracking_number:
            return ''
        return f'https://www.andreani.com/seguimiento?numero={tracking_number}'

    def cancel_shipment(self, tracking_number):
        self.ensure_one()
        if not tracking_number:
            raise UserError(_('Debe proporcionar un número de seguimiento Andreani.'))

        try:
            resp = self._andreani_request(
                'POST',
                f'/v2/ordenes-de-envio/{tracking_number}/cancelar',
                json={'motivo': _('Cancelado desde Odoo')},
            )
        except Exception as err:
            _logger.exception('Error cancelando envío Andreani %s', tracking_number)
            raise UserError(_('Error al cancelar envío Andreani %s: %s') % (tracking_number, str(err)))

        if resp.status_code not in (200, 204):
            try:
                msg = resp.json().get('message', resp.text[:300])
            except Exception:
                msg = resp.text[:300]
            raise UserError(_('Andreani rechazó la cancelación (HTTP %s): %s') % (resp.status_code, msg))

        return True

    def action_test_andreani_credentials(self):
        for carrier in self:
            token = carrier._andreani_get_token(force=True)
            if not token:
                raise UserError(_('No se pudo obtener token de Andreani.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Andreani'),
                'message': _('Conexión exitosa. Token obtenido correctamente.'),
                'type': 'success',
                'sticky': False,
            },
        }
