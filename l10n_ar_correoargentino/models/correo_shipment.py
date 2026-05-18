# -*- coding: utf-8 -*-
import base64
import json
from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .constants import CUSTOMER_VISIBLE_STATES, SHIPMENT_STATE_SELECTION


class CorreoShipment(models.Model):
    _name = 'l10n_ar.correo.shipment'
    _description = 'Envio Correo Argentino'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Referencia', compute='_compute_name', store=True)
    sale_order_id = fields.Many2one('sale.order', string='Pedido', ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Entrega', ondelete='cascade')
    carrier_id = fields.Many2one('delivery.carrier', string='Transportista', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Cliente', required=True, ondelete='restrict')

    state = fields.Selection(SHIPMENT_STATE_SELECTION, string='Estado', default='pending', tracking=True)
    visible_state = fields.Char(string='Estado visible', compute='_compute_visible_state')
    delivery_type = fields.Selection([
        ('D', 'Domicilio'),
        ('S', 'Sucursal'),
    ], string='Tipo entrega')
    product_type = fields.Char(string='Tipo producto')
    product_name = fields.Char(string='Servicio')
    service_type = fields.Char(string='Service Type PaqAr')
    tracking_number = fields.Char(string='Tracking Number', index=True)
    remote_order_id = fields.Char(string='ID remoto')
    agency_code = fields.Char(string='Codigo sucursal')
    agency_name = fields.Char(string='Sucursal')
    agency_address = fields.Char(string='Direccion sucursal')

    latest_status_code = fields.Char(string='Codigo ultimo estado')
    latest_status = fields.Char(string='Ultimo estado')
    latest_event_date = fields.Char(string='Fecha ultimo evento')
    latest_facility = fields.Char(string='Ultima planta')
    latest_event_summary = fields.Char(string='Ultima novedad')

    events_json = fields.Text(string='Tracking JSON')
    request_payload = fields.Text(string='Payload enviado')
    response_payload = fields.Text(string='Respuesta servicio')
    error_message = fields.Text(string='Error')

    label_file = fields.Binary(string='Etiqueta PDF', attachment=True)
    label_filename = fields.Char(string='Nombre etiqueta')

    @api.depends('tracking_number', 'picking_id.name', 'sale_order_id.name')
    def _compute_name(self):
        for shipment in self:
            shipment.name = shipment.tracking_number or shipment.picking_id.name or shipment.sale_order_id.name or _('Envio Correo')

    def _compute_visible_state(self):
        for shipment in self:
            shipment.visible_state = CUSTOMER_VISIBLE_STATES.get(shipment.state)

    def action_refresh_tracking(self):
        for shipment in self:
            if not shipment.tracking_number:
                raise UserError(_('El envio no tiene tracking para consultar.'))
            payload = [{'trackingNumber': shipment.tracking_number}]
            response = shipment.carrier_id._l10n_ar_get_paqar_api().get_tracking(payload, ext_client=shipment.carrier_id.l10n_ar_paqar_ext_client)
            shipment._apply_tracking_response(response)
        return True

    def action_fetch_label(self):
        for shipment in self:
            if not shipment.tracking_number:
                raise UserError(_('El envio no tiene tracking para descargar etiqueta.'))
            payload = [{'sellerId': shipment.carrier_id.l10n_ar_paqar_seller_id or shipment.carrier_id.l10n_ar_paqar_agreement, 'trackingNumber': shipment.tracking_number}]
            response = shipment.carrier_id._l10n_ar_get_paqar_api().get_labels(payload, label_format='10x15')
            shipment._apply_label_response(response)
        return True

    def action_cancel_remote(self):
        for shipment in self:
            if not shipment.tracking_number:
                raise UserError(_('El envio no tiene tracking para cancelar.'))
            response = shipment.carrier_id._l10n_ar_get_paqar_api().cancel_order(shipment.tracking_number)
            shipment.write({
                'state': 'cancelled',
                'response_payload': json.dumps(response, indent=2, ensure_ascii=True),
                'error_message': False,
            })
        return True

    def _apply_label_response(self, response):
        self.ensure_one()
        record = response and response[0] or {}
        file_base64 = record.get('fileBase64')
        values = {
            'response_payload': json.dumps(response, indent=2, ensure_ascii=True),
            'label_filename': record.get('fileName') or record.get('filename'),
        }
        if file_base64:
            values['label_file'] = file_base64
            if self.state == 'pending':
                values['state'] = 'to_post'
        self.write(values)

    def _apply_tracking_response(self, response):
        self.ensure_one()
        record = False
        if isinstance(response, list):
            for item in response:
                if item.get('trackingNumber') == self.tracking_number:
                    record = item
                    break
            if not record and response:
                record = response[0]
        elif isinstance(response, dict):
            record = response
        if not record:
            return
        events = record.get('event') or record.get('events') or []
        latest_event = events[0] if events else {}
        values = {
            'events_json': json.dumps(events, indent=2, ensure_ascii=True),
            'response_payload': json.dumps(response, indent=2, ensure_ascii=True),
            'latest_status_code': latest_event.get('statusId'),
            'latest_status': latest_event.get('status'),
            'latest_event_date': latest_event.get('date'),
            'latest_facility': latest_event.get('facility') or latest_event.get('branch') or latest_event.get('facilityCode'),
            'latest_event_summary': '%s - %s' % ((latest_event.get('status') or '').strip(), (latest_event.get('facility') or latest_event.get('branch') or '').strip()),
            'state': self._map_tracking_state(latest_event),
            'error_message': False,
        }
        self.write(values)

    def _map_tracking_state(self, latest_event):
        status = (latest_event.get('status') or '').upper()
        status_id = (latest_event.get('statusId') or '').upper()
        if not status and self.label_file:
            return 'to_post'
        if 'ENTREG' in status or status_id in ('ENT', 'ECA'):
            return 'delivered'
        if 'DISPONIBLE' in status or 'RETIRO' in status:
            return 'available_for_pickup'
        if 'CANCEL' in status or status_id == 'CAN':
            return 'cancelled'
        if status_id == 'PRE' or 'PREIMPOSICION' in status:
            return 'to_post'
        if 'TRANSIT' in status or 'CLASIFIC' in status or 'DISTRIB' in status:
            return 'in_transit'
        if status or status_id:
            return 'posted'
        return 'pending'

    def action_download_label(self):
        self.ensure_one()
        if not self.label_file:
            raise UserError(_('El envio aun no tiene etiqueta generada.'))
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content?model=l10n_ar.correo.shipment&id=%s&field=label_file&download=true&filename=%s' % (self.id, self.label_filename or 'etiqueta_correo.pdf'),
            'target': 'self',
        }
