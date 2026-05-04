# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Performance Obligations - Async Schedule Regeneration",
    "summary": """Process flagged performance obligations
     asynchronously via queue_job""",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "author": "ACSONE SA/NV",
    "website": "https://github.com/acsone/ifrs15",
    "depends": [
        "account_perf_obligation",
        "queue_job",
    ],
    "data": [
        "data/queue_job_data.xml",
    ],
}
