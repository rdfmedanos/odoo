# -*- coding: utf-8 -*-
{
    'name': 'Argentina - Presupuesto PDF ARCA',
    'version': '1.0.0',
    'summary': 'Impresion de presupuestos en PDF con estilo ARCA',
    'description': """
        Reporte PDF de presupuestos (sale.order) con un diseno
        inspirado en la factura ARCA, simplificado para cotizaciones.
    """,
    'author': 'AgroSentinel',
    'website': 'https://agrosentinel.com',
    'category': 'Sales',
    'depends': ['sale_management', 'l10n_ar_arca'],
    'data': [
        'reports/report_actions.xml',
        'reports/quotation_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
