# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Performance Obligations - Sale",
    "summary": """Automatic performance obligation creation from sale orders""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/ifrs15",
    "depends": [
        "account_perf_obligation_product",
        "account_perf_obligation_start_end_dates",
        "account_perf_obligation_cap",
        "sale",
    ],
    "data": [
        "views/perf_obligation.xml",
        "views/sale_order.xml",
    ],
}
