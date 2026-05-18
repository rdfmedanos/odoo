# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Correo Argentino Ecommerce',
    'version': '19.0.1.0.0',
    'summary': 'MiCorreo y PaqAr para tienda online y logistica',
    'description': """
Integracion de Correo Argentino para Odoo 19 CE.

- Cotizacion web con MiCorreo
- Operacion logistica con PaqAr
- Gestion de envios, etiquetas y tracking
- Portal del cliente con seguimiento
    """,
    'author': 'AgroSentinel',
    'website': 'https://agrosentinel.com',
    'category': 'Website/Website',
    'depends': ['delivery', 'website_sale', 'sale_management', 'sale_stock', 'stock', 'portal'],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_carrier_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/correo_shipment_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_ar_correoargentino/static/src/js/website_sale_correo.js',
            'l10n_ar_correoargentino/static/src/xml/website_sale_correo.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'external_dependencies': {
        'python': ['requests'],
    },
}
