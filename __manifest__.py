# -*- coding: utf-8 -*-

{
    'name': 'Mining Invoice Report',
    'version': '1.0',
    'author': 'Technoindo.com',
    'category': 'Mining Management',
    'depends': [
        'sale_mining',
        'account',
    ],
    'data': [
        # "views/account_invoice_view.xml"
        "views/mining_invoice_report.xml",
        "views/report_mining_invoice.xml"
    ],
    'qweb': [
        # 'static/src/xml/cashback_templates.xml',
    ],
    'demo': [
        # 'demo/sale_agent_demo.xml',
    ],
    "installable": True,
	"auto_instal": False,
	"application": False,
}