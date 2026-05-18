# -*- coding: utf-8 -*-
import json
from requests.auth import HTTPBasicAuth
import requests


class MiCorreoAPI:
    BASE_URLS = {
        'testing': 'https://apitest.correoargentino.com.ar/micorreo/v1',
        'production': 'https://api.correoargentino.com.ar/micorreo/v1',
    }

    def __init__(self, username, password, environment='testing', timeout=30):
        self.username = username or ''
        self.password = password or ''
        self.environment = environment or 'testing'
        self.timeout = timeout
        self.base_url = self.BASE_URLS.get(self.environment, self.BASE_URLS['testing'])

    def _request(self, method, endpoint, headers=None, payload=None, params=None, authenticated=False):
        final_headers = headers.copy() if headers else {}
        url = '%s/%s' % (self.base_url.rstrip('/'), endpoint.lstrip('/'))
        auth = HTTPBasicAuth(self.username, self.password) if endpoint == '/token' else None
        response = requests.request(
            method,
            url,
            headers=final_headers,
            json=payload,
            params=params,
            auth=auth,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise Exception(self._format_error(response))
        if response.text:
            return response.json()
        return {}

    def _format_error(self, response):
        try:
            data = response.json()
        except ValueError:
            data = {'message': response.text}
        message = data.get('message') or data.get('error') or response.reason
        return 'MiCorreo HTTP %s: %s' % (response.status_code, message)

    def get_token(self):
        return self._request('POST', '/token')

    def _bearer_headers(self, token):
        return {
            'Authorization': 'Bearer %s' % token,
            'Content-Type': 'application/json',
        }

    def validate_user(self, token, email, password):
        payload = {'email': email, 'password': password}
        return self._request('POST', '/users/validate', headers=self._bearer_headers(token), payload=payload)

    def register_user(self, token, payload):
        return self._request('POST', '/register', headers=self._bearer_headers(token), payload=payload)

    def get_agencies(self, token, customer_id, province_code, services=None):
        params = {
            'customerId': customer_id,
            'provinceCode': province_code,
        }
        if services:
            params['services'] = services
        return self._request('GET', '/agencies', headers=self._bearer_headers(token), params=params)

    def get_rates(self, token, payload):
        return self._request('POST', '/rates', headers=self._bearer_headers(token), payload=payload)

    def import_shipping(self, token, payload):
        return self._request('POST', '/shipping/import', headers=self._bearer_headers(token), payload=payload)

    def get_tracking(self, token, shipping_id):
        headers = self._bearer_headers(token)
        return self._request('GET', '/shipping/tracking', headers=headers, payload={'shippingId': shipping_id})
