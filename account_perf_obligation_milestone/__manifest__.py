# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Performance Obligation Milestones",
    "summary": "Recognize a performance obligation up to given amounts at "
    "given milestone dates",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/acsone/account-performance-obligation",
    "author": "ACSONE SA/NV",
    "license": "LGPL-3",
    "depends": ["account_perf_obligation_start_end_dates"],
    "data": [
        "security/ir.model.access.csv",
        "security/perf_obligation_milestone_security.xml",
        "views/perf_obligation.xml",
    ],
    "installable": True,
}
