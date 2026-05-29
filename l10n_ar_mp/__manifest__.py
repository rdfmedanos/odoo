# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Mercado Pago',
    'version': '1.0.0',
    'summary': 'Integración con Mercado Pago para Argentina',
    'description': """
        Módulo para integración con Mercado Pago.
        Soporta:
        - Cobros via QR Mercado Pago
        - Link de pago
        - Notificaciones Webhook
    """,
    'author': 'AgroSentinel',
    'website': 'https://agrosentinel.com',
    'category': 'Accounting/Localizations',
    'depends': ['account', 'payment'],
    'data': [
        'security/ir.model.access.csv',
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [
            'requests',
        ],
    },
}
