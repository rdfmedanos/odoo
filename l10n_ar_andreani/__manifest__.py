# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Andreani',
    'version': '19.0.1.0.0',
    'summary': 'Integración de Andreani para cotización y envíos',
    'description': """
Integración de Andreani para Odoo 19 CE.

- Cotización de envíos con API v2 de Andreani
- Generación de órdenes de envío (B2C)
- Descarga de etiquetas PDF
- Seguimiento de envíos
- Cancelación de envíos
    """,
    'author': 'AxialPyme',
    'website': 'https://axialpyme.jaz.ar',
    'category': 'Website/Website',
    'depends': ['delivery', 'sale_stock', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_carrier_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'external_dependencies': {
        'python': ['requests'],
    },
}
