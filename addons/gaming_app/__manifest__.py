# -*- coding: utf-8 -*-
{
    'name': "Playstation App",

    'summary': """""",

    'description': """""",

    'author': "Waleed Hossam",
    'website': "www.linkedin.com/in/waleedhossam",

    'version': '18.0.1.0',
    'license': 'LGPL-3',

    'depends': ['product', 'account', 'purchase', 'mail'],

    'data': [
        'security/ir.model.access.csv',

        'data/ir_sequence_data.xml',
        'data/product_product.xml',
        'data/ir_cron.xml',

        'wizard/payment_workflow_wizard.xml',

        'views/session_session.xml',
        'views/room_type.xml',
        'views/room_name.xml',
        'views/console_type.xml',
        'views/console_number.xml',
        'views/table_tables.xml',
        'views/table_type.xml',
        'views/cafe_order.xml',
        'views/cafe_table.xml',
        'views/menu_items.xml',

        'reports/session_report.xml',
        'reports/cafe_report.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'playstation_app/static/src/xml/dashboard.xml',
            'playstation_app/static/src/css/dashboard.css',
            'playstation_app/static/src/js/dashboard.js',
            'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
        ],
    },

    'application': True,

}
