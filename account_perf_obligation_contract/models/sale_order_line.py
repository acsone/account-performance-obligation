# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_contract_line_values(
        self, contract, predecessor_contract_line_id=False
    ):
        vals = super()._prepare_contract_line_values(
            contract, predecessor_contract_line_id
        )
        if self.perf_obligation_ids:
            vals["perf_obligation_ids"] = [Command.link(self.perf_obligation_ids[0].id)]
        return vals

    def _get_perf_obligation_dates(self):
        """Handle the 'contract' recognition method.

        For contract products, dates come from the SOL's date_start/date_end
        """
        self.ensure_one()
        if self.product_id.perf_obligation_sale_recognition_method == "contract":
            return self.date_start, self.date_end
        return super()._get_perf_obligation_dates()
