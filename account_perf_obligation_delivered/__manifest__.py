# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Performance Obligations - Delivered Amount",
    "summary": """Recognize a delivered (fixed) amount as soon as possible and
     project the remaining balance until the end date""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/account-performance-obligation",
    "depends": [
        "account_perf_obligation_start_end_dates",
    ],
    "data": [
        "views/perf_obligation.xml",
    ],
}
