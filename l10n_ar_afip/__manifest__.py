# -*- coding: utf-8 -*-
{
    'name': 'Argentina - AFIP (compatibilidad)',
    'version': '19.0.1.0.0',
    'summary': 'Puente de compatibilidad hacia l10n_ar_arca',
    'description': """
        Modulo puente para bases que tenian instalado l10n_ar_afip.
        La implementacion activa fue renombrada a l10n_ar_arca.
    """,
    'author': 'AgroSentinel',
    'website': 'https://agrosentinel.com',
    'category': 'Accounting/Localizations',
    'depends': ['l10n_ar_arca'],
    'data': [
        'data/compat_report_templates.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
