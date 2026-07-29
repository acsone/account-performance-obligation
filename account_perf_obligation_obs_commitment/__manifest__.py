# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Performance Obligations - Off-Balance Sheet Commitments",
    "summary": """Manage Off-Balance Sheet Commitments linked to Performance
     Obligations""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/account-performance-obligation",
    "depends": [
        "account_perf_obligation",
        "queue_job",
    ],
    "data": [
        "data/queue_job_function.xml",
        "security/ir.model.access.csv",
        "wizards/perf_obligation_obs_commitment_adjust_wizard.xml",
        "views/res_config_settings.xml",
    ],
}
