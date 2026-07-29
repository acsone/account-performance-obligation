# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Performance Obligations - Sale",
    "summary": """Automatic performance obligation creation from sale orders""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/account-performance-obligation",
    "depends": [
        "account_perf_obligation_start_end_dates",
        "sale",
    ],
    "data": [
        "views/perf_obligation.xml",
        "views/product_template.xml",
        "views/sale_order.xml",
        "views/sale_order_line.xml",
    ],
}
