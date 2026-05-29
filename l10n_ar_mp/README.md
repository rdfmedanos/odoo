# l10n_ar_mp (Odoo 19.0)

Modulo de integracion con Mercado Pago para Argentina en Odoo 19.0.

## Alcance

- Estructura base de integracion con Mercado Pago.
- Soporte previsto para:
  - cobros por QR,
  - links de pago,
  - webhooks.

## Dependencias

- Odoo: `account`, `payment`
- Python: `requests`

Instalacion de dependencia:

```bash
pip3 install requests
```

## Instalacion

1. Copiar `l10n_ar_mp` al `addons_path`.
2. Reiniciar Odoo.
3. Actualizar lista de aplicaciones.
4. Instalar el modulo.

Por consola:

```bash
python3 -m odoo -c /etc/odoo/odoo.conf -d <tu_bd> -i l10n_ar_mp --stop-after-init
```

## Estado actual

El modulo registra Mercado Pago como proveedor estandar de pago de Odoo y agrega campos de credenciales en el formulario de proveedores de pago.

## Configuracion

1. Ir a `Contabilidad / Configuracion / Proveedores de pago`.
2. Abrir `Mercado Pago`.
3. Cargar las credenciales:
   - `Pais de la cuenta Mercado Pago`
   - `Access Token`
   - `Public Key`
   - `Client ID`, si aplica
   - `Client Secret`, si aplica
4. Copiar la `Webhook URL` mostrada por Odoo y configurarla en Mercado Pago.
5. Habilitar el proveedor cuando las credenciales esten listas.

## Endpoints

- Retorno del comprador: `/payment/mercado_pago/return`
- Webhook: `/payment/mercado_pago/webhook`

## Implementacion

El modulo crea ordenes contra la API de Mercado Pago mediante `POST /v1/orders`, usando `Authorization: Bearer <access_token>` y `X-Idempotency-Key`.

El webhook y el retorno consultan la orden en Mercado Pago antes de actualizar el estado de la transaccion de Odoo.

## Pendientes de validacion

- Probar el flujo completo contra una instancia Odoo 19 CE con credenciales sandbox.
- Confirmar los nombres exactos de campos devueltos por Mercado Pago para la URL de checkout en la respuesta de `POST /v1/orders`.
- Ajustar el mapeo de estados si Mercado Pago devuelve valores adicionales para Checkout API Orders.
