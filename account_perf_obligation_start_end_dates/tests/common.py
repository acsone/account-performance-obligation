# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.addons.account_perf_obligation.tests.common import PerfObligationCommon


class PerfObligationDatesCommon(PerfObligationCommon):
    def _create_obligation(
        self,
        perf_type="income",
        total_amount=1000.0,
        recognition_at_date_method=None,
        start_date=None,
        end_date=None,
    ):
        vals = {
            "perf_type": perf_type,
            "total_amount": total_amount,
            "company_id": self.company.id,
        }
        if recognition_at_date_method:
            vals["recognition_at_date_method"] = recognition_at_date_method
        if start_date:
            vals["start_date"] = start_date
        if end_date:
            vals["end_date"] = end_date
        return self.env["perf.obligation"].create(vals)
