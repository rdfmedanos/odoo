# l10n_ar_afip - Facturacion electronica ARCA/AFIP para Odoo 19

Modulo de localizacion para Argentina que agrega facturacion electronica con ARCA (ex AFIP) usando WSAA + WSFEv1.

## Que incluye

- Autenticacion WSAA con certificado y clave privada.
- Solicitud de CAE para facturas y notas de credito/debito de cliente.
- Manejo de entornos `homologacion` y `produccion`.
- Generacion de QR fiscal del comprobante.
- Datos AFIP/ARCA en empresa y factura.
- Reporte PDF de factura ARCA.
- Endpoint API para descargar PDF con token JWT.

## Requisitos

- Odoo 19.
- Modulo base `account` instalado.
- Dependencias Python:
  - `cryptography`
  - `lxml`
  - `requests`
  - `qrcode`
  - `Pillow`
  - `PyJWT`

Instalacion de dependencias (ejemplo):

```bash
pip3 install cryptography lxml requests qrcode Pillow PyJWT
```

## Instalacion del modulo

1. Copiar la carpeta `l10n_ar_afip` dentro de un `addons_path` de Odoo.
2. Reiniciar Odoo.
3. En Odoo, ir a **Apps** -> **Actualizar lista de aplicaciones**.
4. Buscar `Argentina - AFIP Facturacion Electronica` e instalar.

### Instalacion por consola (opcional)

```bash
python3 -m odoo -c /etc/odoo/odoo.conf -d <tu_bd> -i l10n_ar_afip --stop-after-init
```

## Configuracion inicial

### 1) Empresa (AFIP)

En **Ajustes / Empresa** (pestana AFIP del modulo):

- Cargar CUIT.
- Seleccionar entorno (`homologacion` o `produccion`).
- Cargar certificado y clave privada (archivo o texto PEM).
- Completar Ingresos Brutos e Inicio de actividades si corresponde.

### 2) Diario de ventas

En el diario de facturacion:

- Configurar Punto de Venta AFIP (`l10n_ar_afip_pto_vta`).
- Tipo de comprobante AFIP por defecto (A/B/C).
- Activar autorizacion automatica si queres CAE al publicar.

### 3) Facturas

En facturas de cliente:

- Publicar factura.
- Solicitar CAE desde la pestana AFIP (o automaticamente si esta activado).
- Verificar `CAE`, `Fecha Vencimiento CAE`, `Resultado AFIP` y QR.

## Reporte PDF

- El modulo agrega y usa el reporte ARCA para `account.move`.
- Incluye datos de cabecera, detalle, totales, CAE, QR y leyenda fiscal.

## API de PDF (JWT)

Endpoint:

```text
GET /api/billing/invoices/<invoice_id>/pdf?token=<jwt>
```

Configurar secreto JWT en parametro del sistema:

- Clave: `l10n_ar_afip.jwt_secret`

## Notas de homologacion

- En entorno homologacion, la validacion publica puede no mostrar el mismo resultado que produccion.
- Para pruebas reales de consulta publica del comprobante, usar CAE emitido en produccion.

## Problemas comunes

- **No aparece el modulo en Apps**: revisar `addons_path`, permisos y actualizar lista de apps.
- **No genera QR**: verificar dependencias `qrcode` y `Pillow`.
- **No autoriza CAE**: revisar certificado, clave, CUIT, punto de venta y entorno.
- **QR no valida**: recalcular QR en facturas existentes luego de cambios de formato/url.

## Estructura principal

- `models/res_company.py`: configuracion AFIP en empresa.
- `models/account_move.py`: CAE, QR y logica de facturas.
- `services/wsaa.py`: autenticacion WSAA.
- `services/wsfe.py`: consumo WSFEv1.
- `reports/invoice_afip_report.xml`: plantilla PDF.
- `controllers/main.py`: endpoints API.
