# -*- coding: utf-8 -*-
{
    'name': 'Customs EORI Validation',
    'version': '1.0',
    'author': 'XCLUDE AB',
    'website': 'https://www.xclude.se',
    'category': 'Logistics/Customs',
    'license': 'LGPL-3',
    'description': """
Customs EORI Validation for Partner's EORI Numbers
==================================================
This module adds validation for EU and UK (GB) EORI numbers in Odoo, ensuring compliance with customs regulations.
    """,
    'depends': ['account'],
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'external_dependencies': {
        'python': ['zeep'],
    },
}
