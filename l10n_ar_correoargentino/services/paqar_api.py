# -*- coding: utf-8 -*-
import requests


class PaqArAPI:
    BASE_URLS = {
        'testing': 'https://apitest.correoargentino.com.ar/paqar/v1',
        'production': 'https://api.correoargentino.com.ar/paqar/v1',
    }

    def __init__(self, api_key, agreement, environment='testing', timeout=30):
        self.api_key = api_key or ''
        self.agreement = agreement or ''
        self.environment = environment or 'testing'
        self.timeout = timeout
        self.base_url = self.BASE_URLS.get(self.environment, self.BASE_URLS['testing'])

    def _headers(self):
        return {
            'Authorization': 'Apikey %s' % self.api_key,
            'agreement': self.agreement,
            'Content-Type': 'application/json',
        }

    def _request(self, method, endpoint, payload=None, params=None):
        response = requests.request(
            method,
            '%s/%s' % (self.base_url.rstrip('/'), endpoint.lstrip('/')),
            headers=self._headers(),
            json=payload,
            params=params,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise Exception(self._format_error(response))
        if response.status_code == 204 or not response.text:
            return {}
        return response.json()

    def _format_error(self, response):
        try:
            data = response.json()
        except ValueError:
            data = {'message': response.text}
        message = data.get('message') or data.get('error') or response.reason
        return 'PaqAr HTTP %s: %s' % (response.status_code, message)

    def auth(self):
        return self._request('GET', '/auth')

    def create_order(self, payload):
        return self._request('POST', '/orders', payload=payload)

    def cancel_order(self, tracking_number):
        return self._request('PATCH', '/orders/%s/cancel' % tracking_number)

    def get_labels(self, payload, label_format='10x15'):
        return self._request('POST', '/labels', payload=payload, params={'labelFormat': label_format})

    def get_tracking(self, tracking_numbers, ext_client=None):
        params = {}
        if ext_client:
            params['extClient'] = ext_client
        return self._request('GET', '/tracking', payload=tracking_numbers, params=params)

    def get_agencies(self, state_id=None, pickup_availability=None, package_reception=None):
        params = {}
        if state_id:
            params['stateId'] = state_id
        if pickup_availability is not None:
            params['pickup_availability'] = pickup_availability
        if package_reception is not None:
            params['package_reception'] = package_reception
        return self._request('GET', '/agencies', params=params)
