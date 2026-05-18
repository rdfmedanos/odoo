/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc";

publicWidget.registry.CorreoArgentinoCart = publicWidget.Widget.extend({
    selector: '#o_wsale_correo_quote',
    events: {
        'change .js_correo_delivery_type': '_onDeliveryTypeChange',
        'click .js_correo_fetch_agencies': '_onFetchAgencies',
        'click .js_correo_quote': '_onQuote',
        'click .js_correo_apply_rate': '_onApplyRate',
    },

    start() {
        this._toggleAgencyMode();
        return this._super(...arguments);
    },

    _onDeliveryTypeChange() {
        this._toggleAgencyMode();
    },

    _toggleAgencyMode() {
        const isAgency = this.el.querySelector('.js_correo_delivery_type').value === 'S';
        this.el.querySelector('.js_correo_province_wrapper').classList.toggle('d-none', !isAgency);
        this.el.querySelector('.js_correo_agency_wrapper').classList.toggle('d-none', !isAgency);
        this.el.querySelector('.js_correo_fetch_agencies').classList.toggle('d-none', !isAgency);
    },

    async _onFetchAgencies() {
        this._clearError();
        const carrierId = this.el.querySelector('.js_correo_carrier_id').value;
        const provinceCode = this.el.querySelector('.js_correo_province_code').value;
        if (!provinceCode) {
            this._showError('Selecciona una provincia para cargar sucursales.');
            return;
        }
        const result = await jsonrpc('/shop/correoargentino/agencies', {carrier_id: carrierId, province_code: provinceCode});
        if (!result.ok) {
            this._showError(result.error || 'No se pudieron cargar las sucursales.');
            return;
        }
        const select = this.el.querySelector('.js_correo_agency_select');
        select.innerHTML = '';
        result.agencies.forEach((agency) => {
            const option = document.createElement('option');
            option.value = agency.code;
            option.textContent = `${agency.name} - ${agency.address || ''}`;
            option.dataset.name = agency.name;
            option.dataset.address = agency.address || '';
            select.appendChild(option);
        });
    },

    async _onQuote() {
        this._clearError();
        const carrierId = this.el.querySelector('.js_correo_carrier_id').value;
        const postalCode = this.el.querySelector('.js_correo_postal_code').value;
        const deliveryType = this.el.querySelector('.js_correo_delivery_type').value;
        const provinceCode = this.el.querySelector('.js_correo_province_code').value;
        const agencySelect = this.el.querySelector('.js_correo_agency_select');
        const option = agencySelect.options[agencySelect.selectedIndex];
        const payload = {
            carrier_id: carrierId,
            postal_code: postalCode,
            province_code: provinceCode,
            delivery_type: deliveryType,
            agency_code: option ? option.value : false,
            agency_name: option ? option.dataset.name : false,
            agency_address: option ? option.dataset.address : false,
        };
        const result = await jsonrpc('/shop/correoargentino/quote', payload);
        if (!result.ok) {
            this._showError(result.error || 'No se pudo cotizar el envio.');
            return;
        }
        this._renderRates(carrierId, result.rates || []);
    },

    _renderRates(carrierId, rates) {
        const container = this.el.querySelector('.js_correo_rates');
        container.classList.remove('d-none');
        container.innerHTML = '';
        if (!rates.length) {
            container.innerHTML = '<div class="alert alert-warning">No se encontraron tarifas para este destino.</div>';
            return;
        }
        rates.forEach((rate) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'border rounded p-2 mb-2';
            wrapper.innerHTML = `
                <div class="fw-bold">${rate.productName || 'Correo Argentino'}</div>
                <div>Tipo: ${rate.deliveredType === 'S' ? 'Sucursal' : 'Domicilio'}</div>
                <div>Precio: $${rate.price}</div>
                <div>Plazo: ${rate.deliveryTimeMin || '-'} a ${rate.deliveryTimeMax || '-'} dias</div>
                <button type="button" class="btn btn-sm btn-primary mt-2 js_correo_apply_rate">Aplicar envio</button>
            `;
            wrapper.querySelector('.js_correo_apply_rate').dataset.carrierId = carrierId;
            wrapper.querySelector('.js_correo_apply_rate').dataset.rate = JSON.stringify(rate);
            container.appendChild(wrapper);
        });
    },

    async _onApplyRate(ev) {
        this._clearError();
        const button = ev.currentTarget;
        const result = await jsonrpc('/shop/correoargentino/select_rate', {
            carrier_id: button.dataset.carrierId,
            rate: button.dataset.rate,
        });
        if (!result.ok) {
            this._showError(result.error || 'No se pudo aplicar la tarifa seleccionada.');
            return;
        }
        window.location.reload();
    },

    _showError(message) {
        const error = this.el.querySelector('.js_correo_error');
        error.textContent = message;
        error.classList.remove('d-none');
    },

    _clearError() {
        const error = this.el.querySelector('.js_correo_error');
        error.textContent = '';
        error.classList.add('d-none');
    },
});
