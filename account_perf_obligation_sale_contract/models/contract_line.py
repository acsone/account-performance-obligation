# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class ContractLine(models.Model):
    _inherit = "contract.line"

    def _update_perf_obligation_from_sol(self, sol):
        """After a contract line is created from a SOL, link the PO to the
        contract line and sync its dates."""
        self.ensure_one()
        po = self.perf_obligation_ids
        if not po:
            return
        po.write(
            {
                "contract_line_id": self.id,
                "start_date": self.date_start,
                "end_date": self.date_end,
            }
        )
