# -*- coding: utf-8 -*-
{
    'name': 'Argentina - AFIP Facturación Electrónica',
    'version': '1.0.0',
    'summary': 'Facturación Electrónica ARCA/AFIP para Argentina',
    'description': """
        Módulo para facturación electrónica con ARCA (ex AFIP) usando WSFEv1.
        Soporta:
        - Autenticación WSAA con certificado digital
        - Solicitud de CAE via WSFE
        - Manejo de entornos homologación y producción
        - Refresh automático de tokens
    """,
    'author': 'AgroSentinel',
    'website': 'https://agrosentinel.com',
    'category': 'Accounting/Localizations',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/account_move_views.xml',
        'views/clipboard_views.xml',
        'views/message_wizard_views.xml',
        'reports/report_actions.xml',
        'reports/invoice_report.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [
            'cryptography',
            'lxml',
            'requests',
        ],
    },
}
