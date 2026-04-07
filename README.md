# Modulos Argentina para Odoo 19.0

Repositorio con modulos de localizacion para Odoo 19.0.

## Modulos incluidos

- `l10n_ar_arca`: facturacion electronica ARCA/AFIP (WSAA + WSFEv1, CAE, QR y reporte PDF).
- `l10n_ar_mp`: integracion base con Mercado Pago para cobros en Argentina.
- `l10n_ar_ticketarca`: ticket POS con datos ARCA/AFIP (CAE, QR, codigo de barras) y impresion automatica.

## Requisitos generales

- Odoo 19.0
- Python 3
- Modulos base de Odoo segun cada addon (`account`, `payment`)

## Instalacion rapida

1. Copiar los modulos al `addons_path` de Odoo.
2. Reiniciar servicio Odoo.
3. Actualizar lista de apps desde Odoo.
4. Instalar los modulos necesarios.

Por consola:

```bash
python3 -m odoo -c /etc/odoo/odoo.conf -d <tu_bd> -i l10n_ar_arca,l10n_ar_mp,l10n_ar_ticketarca --stop-after-init
```

## Documentacion por modulo

- `l10n_ar_arca/README.md`
- `l10n_ar_mp/README.md`
- `l10n_ar_ticketarca/README.md`
