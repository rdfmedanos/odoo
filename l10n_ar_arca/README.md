# l10n_ar_arca (Odoo 19.0)

Modulo de facturacion electronica ARCA/AFIP para Argentina en Odoo 19.0.

## Alcance

- Configuracion AFIP por empresa.
- Autenticacion WSAA con certificado y clave privada.
- Solicitud de CAE por WSFEv1.
- Generacion de QR fiscal del comprobante.
- Reporte PDF de factura ARCA.
- API para descarga de PDF con JWT.

## Dependencias

- Odoo: `account`
- Python: `cryptography`, `lxml`, `requests`, `qrcode`, `Pillow`, `PyJWT`

Instalacion de dependencias:

```bash
pip3 install cryptography lxml requests qrcode Pillow PyJWT
```

## Instalacion

1. Copiar `l10n_ar_arca` al `addons_path`.
2. Reiniciar Odoo.
3. Actualizar lista de aplicaciones.
4. Instalar el modulo.

Por consola:

```bash
python3 -m odoo -c /etc/odoo/odoo.conf -d <tu_bd> -i l10n_ar_arca --stop-after-init
```

## Configuracion minima

1. Empresa:
   - CUIT
   - Entorno (`homologacion` o `produccion`)
   - Certificado y clave privada
2. Diario de ventas:
   - Punto de venta AFIP
   - Tipo de comprobante
3. Factura:
   - Publicar
   - Solicitar CAE (manual o automatico)

## Nota de homologacion

En homologacion, la consulta publica del QR puede no mostrar el mismo resultado que en produccion.
