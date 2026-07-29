# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Perf Obligation Sale Contract",
    "summary": """Bridge module between `account_perf_obligation_sale`,
    `account_perf_obligation_contract` and `product_contract`""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/account-performance-obligation",
    "depends": [
        "account_perf_obligation_contract",
        "account_perf_obligation_sale",
        "product_contract",
    ],
    "data": [
        "views/product_template.xml",
    ],
}
