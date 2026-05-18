# -*- coding: utf-8 -*-
import json
from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    l10n_ar_correo_shipment_ids = fields.One2many('l10n_ar.correo.shipment', 'picking_id', string='Envios Correo')
    l10n_ar_correo_shipment_count = fields.Integer(string='Cantidad envios Correo', compute='_compute_l10n_ar_correo_shipment_count')

    def _compute_l10n_ar_correo_shipment_count(self):
        for picking in self:
            picking.l10n_ar_correo_shipment_count = len(picking.l10n_ar_correo_shipment_ids)

    def button_validate(self):
        result = super().button_validate()
        done_pickings = self.filtered(lambda p: p.state == 'done')
        for picking in done_pickings:
            sale_order = picking.sale_id
            if not sale_order or not sale_order.carrier_id or sale_order.carrier_id.delivery_type != 'l10n_ar_correoargentino':
                continue
            if not picking.l10n_ar_correo_shipment_ids:
                try:
                    picking.action_create_correo_shipment()
                except Exception as err:
                    self.env['l10n_ar.correo.shipment'].create({
                        'sale_order_id': sale_order.id,
                        'picking_id': picking.id,
                        'carrier_id': sale_order.carrier_id.id,
                        'partner_id': sale_order.partner_shipping_id.id or sale_order.partner_id.id,
                        'delivery_type': sale_order.l10n_ar_correo_delivery_type,
                        'product_type': sale_order.l10n_ar_correo_product_type or sale_order.carrier_id.l10n_ar_default_product_type,
                        'product_name': sale_order.l10n_ar_correo_product_name,
                        'state': 'error',
                        'error_message': str(err),
                    })
        return result

    def action_view_l10n_ar_correo_shipments(self):
        self.ensure_one()
        action = self.env.ref('l10n_ar_correoargentino.l10n_ar_correo_shipment_action').read()[0]
        action['domain'] = [('picking_id', '=', self.id)]
        return action

    def action_create_correo_shipment(self):
        shipments = self.env['l10n_ar.correo.shipment']
        for picking in self:
            sale_order = picking.sale_id
            carrier = sale_order.carrier_id
            if not carrier or carrier.delivery_type != 'l10n_ar_correoargentino':
                raise UserError(_('La entrega no tiene configurado Correo Argentino como transportista.'))
            if picking.l10n_ar_correo_shipment_ids:
                shipments |= picking.l10n_ar_correo_shipment_ids
                continue
            payload = picking._l10n_ar_build_paqar_payload()
            response = carrier._l10n_ar_get_paqar_api().create_order(payload)
            shipment = self.env['l10n_ar.correo.shipment'].create({
                'sale_order_id': sale_order.id,
                'picking_id': picking.id,
                'carrier_id': carrier.id,
                'partner_id': sale_order.partner_shipping_id.id or sale_order.partner_id.id,
                'delivery_type': sale_order.l10n_ar_correo_delivery_type,
                'product_type': sale_order.l10n_ar_correo_product_type or carrier.l10n_ar_default_product_type,
                'product_name': sale_order.l10n_ar_correo_product_name,
                'service_type': sale_order.l10n_ar_correo_product_type or carrier.l10n_ar_default_product_type,
                'tracking_number': response.get('trackingNumber'),
                'remote_order_id': response.get('id') or response.get('trackingNumber'),
                'agency_code': sale_order.l10n_ar_correo_agency_code,
                'agency_name': sale_order.l10n_ar_correo_agency_name,
                'agency_address': sale_order.l10n_ar_correo_agency_address,
                'request_payload': json.dumps(payload, indent=2, ensure_ascii=True),
                'response_payload': json.dumps(response, indent=2, ensure_ascii=True),
                'state': 'pending',
            })
            shipment.action_fetch_label()
            shipments |= shipment
        return self.action_view_l10n_ar_correo_shipments() if len(self) == 1 else True

    def _l10n_ar_build_paqar_payload(self):
        self.ensure_one()
        sale_order = self.sale_id
        carrier = sale_order.carrier_id
        partner = sale_order.partner_shipping_id or sale_order.partner_id
        province_code = carrier._l10n_ar_get_partner_province_code(partner)
        dimensions = carrier._l10n_ar_get_package_values(sale_order)
        delivery_type = 'homeDelivery' if sale_order.l10n_ar_correo_delivery_type == 'D' else 'agency'
        return {
            'sellerId': carrier.l10n_ar_paqar_seller_id or carrier.l10n_ar_paqar_agreement,
            'trackingNumber': '',
            'order': {
                'senderData': {
                    'id': carrier.l10n_ar_paqar_agreement,
                    'businessName': carrier.l10n_ar_origin_business_name or self.company_id.name,
                    'phoneNumber': carrier.l10n_ar_origin_phone or '',
                    'cellphoneNumber': carrier.l10n_ar_origin_cellphone or '',
                    'email': carrier.l10n_ar_origin_email or '',
                    'observation': sale_order.name,
                    'address': {
                        'streetName': carrier.l10n_ar_origin_street_name or '',
                        'streetNumber': carrier.l10n_ar_origin_street_number or '',
                        'cityName': carrier.l10n_ar_origin_city or '',
                        'floor': carrier.l10n_ar_origin_floor or '',
                        'department': carrier.l10n_ar_origin_apartment or '',
                        'state': carrier.l10n_ar_origin_province_code or '',
                        'zipCode': carrier.l10n_ar_origin_postal_code or '',
                    },
                },
                'shippingData': {
                    'name': partner.name or '',
                    'phoneNumber': partner.phone or '',
                    'cellphoneNumber': partner.mobile or '',
                    'email': partner.email or '',
                    'observation': sale_order.name,
                    'address': {
                        'streetName': partner.street or '',
                        'streetNumber': partner.street2 or '',
                        'cityName': partner.city or '',
                        'floor': '',
                        'department': '',
                        'state': province_code or sale_order.l10n_ar_correo_destination_province_code or '',
                        'zipCode': sale_order.l10n_ar_correo_destination_postal_code or partner.zip or '',
                    },
                },
                'parcels': [{
                    'dimensions': {
                        'height': str(dimensions['height']),
                        'width': str(dimensions['width']),
                        'depth': str(dimensions['length']),
                    },
                    'productWeight': str(dimensions['weight']),
                    'productCategory': 'ecommerce',
                    'declaredValue': str(sale_order.amount_total),
                }],
                'deliveryType': delivery_type,
                'agencyId': sale_order.l10n_ar_correo_agency_code or '',
                'saleDate': fields.Datetime.now().isoformat(),
                'shipmentClientId': sale_order.name,
                'serviceType': sale_order.l10n_ar_correo_product_type or carrier.l10n_ar_default_product_type or 'CP',
            },
        }

    def action_fetch_correo_label(self):
        self.mapped('l10n_ar_correo_shipment_ids').action_fetch_label()
        return True

    def action_refresh_correo_tracking(self):
        self.mapped('l10n_ar_correo_shipment_ids').action_refresh_tracking()
        return True

    def action_cancel_correo_shipment(self):
        self.mapped('l10n_ar_correo_shipment_ids').action_cancel_remote()
        return True
