# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Ticket ARCA POS',
    'version': '1.0.0',
    'summary': 'Imprime datos ARCA/AFIP en ticket de TPV',
    'description': """
        Extiende el ticket de Punto de Venta para mostrar datos ARCA/AFIP:
        - CAE
        - Fecha de vencimiento de CAE
        - Codigo QR oficial
    """,
    'author': 'AgroSentinel',
    'website': 'https://agrosentinel.com',
    'category': 'Accounting/Localizations',
    'depends': ['point_of_sale', 'l10n_ar_arca'],
    'data': [
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_ar_ticketarca/static/src/css/pos_receipts.css',
            'l10n_ar_ticketarca/static/src/js/receipt_afip_data_patch.js',
            'l10n_ar_ticketarca/static/src/js/auto_print_on_payment_patch.js',
            'l10n_ar_ticketarca/static/src/xml/order_receipt_afip.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
