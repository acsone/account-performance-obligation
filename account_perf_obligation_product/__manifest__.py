# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Performance Obligations - Product Configuration",
    "summary": """Configure automatic performance obligation creation on products""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/ifrs15",
    "depends": [
        "product",
        "account_perf_obligation",
    ],
    "data": [
        "views/product_template.xml",
    ],
}
