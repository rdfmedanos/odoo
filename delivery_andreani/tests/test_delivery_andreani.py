# -*- coding: utf-8 -*-
import base64
from unittest.mock import patch, MagicMock
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestDeliveryAndreani(TransactionCase):

    def setUp(self):
        super().setUp()
        self.carrier = self.env['delivery.carrier'].create({
            'name': 'Andreani Test',
            'delivery_type': 'andreani',
            'andreani_username': 'test_user',
            'andreani_password': 'test_pass',
            'andreani_client_number': '123456',
            'andreani_contract_number': '789012',
            'andreani_env': 'test',
            'andreani_volumetric_divisor': 5000,
        })
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'weight': 0.5,
            'type': 'product',
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'zip': '2000',
            'street': 'Av. Siempre Viva 123',
            'city': 'Rosario',
            'email': 'test@example.com',
            'phone': '3415555555',
        })
        self.company = self.env.company
        self.company.write({'zip': '1000'})

    def _create_sale_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        order.action_confirm()
        return order

    def test_01_base_url_test_env(self):
        self.assertEqual(self.carrier._andreani_base_url(), 'https://apisqa.andreani.com')

    def test_02_base_url_prod_env(self):
        self.carrier.andreani_env = 'prod'
        self.assertEqual(self.carrier._andreani_base_url(), 'https://apis.andreani.com')

    def test_03_get_credentials_from_carrier(self):
        creds = self.carrier._andreani_get_credentials()
        self.assertEqual(creds['username'], 'test_user')
        self.assertEqual(creds['password'], 'test_pass')
        self.assertEqual(creds['client_number'], '123456')
        self.assertEqual(creds['contract_number'], '789012')
        self.assertEqual(creds['env'], 'test')

    def test_04_get_credentials_from_global_config(self):
        carrier = self.env['delivery.carrier'].create({
            'name': 'Andreani Global',
            'delivery_type': 'andreani',
        })
        IrConfig = self.env['ir.config_parameter'].sudo()
        IrConfig.set_param('delivery_andreani.username', 'global_user')
        IrConfig.set_param('delivery_andreani.password', 'global_pass')
        IrConfig.set_param('delivery_andreani.client_number', '654321')
        IrConfig.set_param('delivery_andreani.contract_number', '098765')
        IrConfig.set_param('delivery_andreani.env', 'prod')

        creds = carrier._andreani_get_credentials()
        self.assertEqual(creds['username'], 'global_user')
        self.assertEqual(creds['password'], 'global_pass')
        self.assertEqual(creds['client_number'], '654321')

    def test_05_get_token_cached(self):
        self.carrier.write({
            'andreani_token': 'cached_token_123',
            'andreani_token_expires': fields.Datetime.now() + timedelta(hours=10),
        })
        token = self.carrier._andreani_get_token(force=False)
        self.assertEqual(token, 'cached_token_123')

    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_06_get_token_fresh(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'x-authorization-token': 'new_token_456'}
        mock_post.return_value = mock_resp

        token = self.carrier._andreani_get_token(force=True)
        self.assertEqual(token, 'new_token_456')
        self.assertEqual(self.carrier.andreani_token, 'new_token_456')
        self.assertTrue(self.carrier.andreani_token_expires > fields.Datetime.now())

    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_07_get_token_auth_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {'message': 'Unauthorized'}
        mock_resp.text = 'Unauthorized'
        mock_post.return_value = mock_resp

        with self.assertRaises(UserError):
            self.carrier._andreani_get_token(force=True)

    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_08_get_token_no_credentials(self, mock_post):
        carrier = self.env['delivery.carrier'].create({
            'name': 'No Creds',
            'delivery_type': 'andreani',
        })
        with self.assertRaises(UserError):
            carrier._andreani_get_token(force=True)

    def test_09_rate_configuration_error_ok(self):
        self.assertFalse(self.carrier._andreani_get_rate_configuration_error())

    def test_10_rate_configuration_error_no_creds(self):
        carrier = self.env['delivery.carrier'].create({
            'name': 'No Creds',
            'delivery_type': 'andreani',
        })
        self.assertTrue(carrier._andreani_get_rate_configuration_error())

    def test_11_rate_configuration_error_no_client(self):
        carrier = self.env['delivery.carrier'].create({
            'name': 'No Client',
            'delivery_type': 'andreani',
            'andreani_username': 'u',
            'andreani_password': 'p',
        })
        self.assertTrue(carrier._andreani_get_rate_configuration_error())

    def test_12_get_tracking_link(self):
        link = self.carrier.get_tracking_link('ANDR123456')
        self.assertIn('ANDR123456', link)
        self.assertTrue(link.startswith('https://'))

    def test_13_get_tracking_link_empty(self):
        link = self.carrier.get_tracking_link('')
        self.assertEqual(link, '')

    @patch('delivery_andreani.models.delivery_carrier.requests.get')
    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_14_rate_shipment_success(self, mock_post, mock_get):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.headers = {'x-authorization-token': 'rate_token'}
        mock_post.return_value = mock_login

        mock_rates = MagicMock()
        mock_rates.status_code = 200
        mock_rates.json.return_value = {'tarifa': 1500.0}
        mock_get.return_value = mock_rates

        order = self._create_sale_order()
        result = self.carrier.andreani_rate_shipment(order)
        self.assertTrue(result['success'])
        self.assertEqual(result['price'], 1500.0)

    @patch('delivery_andreani.models.delivery_carrier.requests.get')
    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_15_rate_shipment_no_price(self, mock_post, mock_get):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.headers = {'x-authorization-token': 'rate_token'}
        mock_post.return_value = mock_login

        mock_rates = MagicMock()
        mock_rates.status_code = 200
        mock_rates.json.return_value = {}
        mock_get.return_value = mock_rates

        order = self._create_sale_order()
        result = self.carrier.andreani_rate_shipment(order)
        self.assertFalse(result['success'])

    @patch('delivery_andreani.models.delivery_carrier.requests.get')
    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_16_send_shipping_success(self, mock_post, mock_get):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.headers = {'x-authorization-token': 'ship_token'}

        mock_create = MagicMock()
        mock_create.status_code = 201
        mock_create.json.return_value = {
            'numeroAndreani': 'ANDR789',
            'tarifa': 1500.0,
        }

        mock_label = MagicMock()
        mock_label.status_code = 200
        mock_label.content = b'%PDF-1.4 fake pdf content'

        mock_post.side_effect = [mock_login, mock_create]
        mock_get.return_value = mock_label

        order = self._create_sale_order()
        pickings = order.picking_ids
        self.assertTrue(pickings)

        result = self.carrier.andreani_send_shipping(pickings)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tracking_number'], 'ANDR789')
        self.assertEqual(result[0]['exact_price'], 1500.0)
        self.assertEqual(pickings.carrier_tracking_ref, 'ANDR789')

    @patch('delivery_andreani.models.delivery_carrier.requests.get')
    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_17_send_shipping_no_label(self, mock_post, mock_get):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.headers = {'x-authorization-token': 'ship_token'}

        mock_create = MagicMock()
        mock_create.status_code = 201
        mock_create.json.return_value = {
            'numeroAndreani': 'ANDR789',
            'tarifa': 1500.0,
        }

        mock_label = MagicMock()
        mock_label.status_code = 404

        mock_post.side_effect = [mock_login, mock_create]
        mock_get.return_value = mock_label

        order = self._create_sale_order()
        pickings = order.picking_ids
        result = self.carrier.andreani_send_shipping(pickings)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['tracking_number'], 'ANDR789')

    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_18_cancel_shipment_success(self, mock_post):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.headers = {'x-authorization-token': 'cancel_token'}

        mock_cancel = MagicMock()
        mock_cancel.status_code = 200

        mock_post.side_effect = [mock_login, mock_cancel]

        result = self.carrier.cancel_shipment('ANDR789')
        self.assertTrue(result)

    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_19_cancel_shipment_error(self, mock_post):
        mock_login = MagicMock()
        mock_login.status_code = 200
        mock_login.headers = {'x-authorization-token': 'cancel_token'}

        mock_cancel = MagicMock()
        mock_cancel.status_code = 400
        mock_cancel.json.return_value = {'message': 'Cannot cancel'}
        mock_cancel.text = 'Cannot cancel'

        mock_post.side_effect = [mock_login, mock_cancel]

        with self.assertRaises(UserError):
            self.carrier.cancel_shipment('ANDR789')

    def test_20_cancel_shipment_no_tracking(self):
        with self.assertRaises(UserError):
            self.carrier.cancel_shipment('')

    def test_21_package_data_from_order(self):
        order = self._create_sale_order()
        package = self.carrier._andreani_get_package_data(order)
        self.assertEqual(package['weight'], 1000)  # 0.5 kg * 2 qty * 1000
        self.assertTrue(package['height'] > 0)

    def test_22_volumetric_weight_computation(self):
        package = {'length': 20, 'width': 15, 'height': 10}
        vol_weight = self.carrier._andreani_compute_volumetric_weight(package)
        expected = (20 * 15 * 10) / 5000
        self.assertEqual(vol_weight, expected)

    @patch('delivery_andreani.models.delivery_carrier.requests.post')
    def test_23_action_test_andreani_credentials(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {'x-authorization-token': 'test_token'}
        mock_post.return_value = mock_resp

        result = self.carrier.action_test_andreani_credentials()
        self.assertIn('display_notification', result.get('tag', ''))
        self.assertEqual(result['params']['type'], 'success')
