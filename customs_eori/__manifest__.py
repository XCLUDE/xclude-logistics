{
    'name': 'Customs EORI Validation',
    'version': '19.0.1.0.0',
    'author': 'XCLUDE',
    'website': 'https://www.xclude.se',
    'category': 'Logistics/Customs',
    'license': 'LGPL-3',
    'summary': 'Validates EU and UK (GB) EORI numbers for partners in Odoo.',
    'description': """
Customs EORI Validation for Partner's EORI Numbers
==================================================
This module adds validation for EU and UK (GB) EORI numbers in Odoo, ensuring compliance with customs regulations.
    """,
    'depends': ['account'],
    'external_dependencies': {'python': ['zeep']},
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
