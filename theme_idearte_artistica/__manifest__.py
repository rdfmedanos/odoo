# -*- coding: utf-8 -*-
{
    'name': 'Theme Idearte Artística',
    'description': 'Tema personalizado para Idearte Artística - Tienda de fibrofácil, taller artístico y servicios de Router CNC.',
    'category': 'Theme/Creative',
    'version': '19.0.1.0.0',
    'author': 'Antigravity / AgroSentinel',
    'website': 'https://idearteartistica.com',
    'depends': ['website', 'website_sale'],
    'data': [
        'views/snippets/hero.xml',
        'views/snippets/categories.xml',
        'views/snippets/featured_products.xml',
        'views/snippets/local_experience.xml',
        'views/snippets/gallery.xml',
        'views/snippets/cnc_section.xml',
        'views/snippets/final_cta.xml',
        'views/snippets.xml',
        'views/homepage.xml',
        'views/brand_promotion.xml',
        'views/category_filmstrip.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'theme_idearte_artistica/static/src/js/theme_idearte_ui.js',
            'theme_idearte_artistica/static/src/xml/theme_idearte_notifications.xml',
            'theme_idearte_artistica/static/src/scss/variables.scss',
            'theme_idearte_artistica/static/src/scss/style.scss',
        ],
    },
    'images': [
        'static/src/img/logo.png',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
