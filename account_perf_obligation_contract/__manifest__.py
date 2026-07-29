# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Performance Obligations - Contract",
    "summary": """Automatic performance obligation creation from contracts""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/account-performance-obligation",
    "depends": [
        "account_perf_obligation_start_end_dates",
        "contract_service_dates",
    ],
    "data": [
        "views/perf_obligation.xml",
        "views/contract_contract.xml",
        "views/contract_line.xml",
    ],
}
