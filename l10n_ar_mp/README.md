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

El modulo esta en base inicial y puede requerir desarrollos adicionales segun el flujo de cobro que necesites.
