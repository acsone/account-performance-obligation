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

    def create_contract_line(self, contract):
        result = super().create_contract_line(contract)
        for rec in self:
            contract_line = contract.contract_line_ids.filtered(
                lambda line, rec=rec: line.sale_order_line_id == rec
            )
            if contract_line and rec.perf_obligation_ids:
                contract_line._update_perf_obligation_from_sol(rec)
        return result
