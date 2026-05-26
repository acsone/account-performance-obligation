# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_contract_line_values(
        self, contract, predecessor_contract_line_id=False
    ):
        """
        Creating a contract line from a sale order line with obligation
        removes the obligation from the sale order line and sets it
        on the contract line
        """
        vals = super()._prepare_contract_line_values(
            contract, predecessor_contract_line_id
        )
        if self.product_id.perf_obligation_sale_auto_create:
            vals.update(
                {
                    "perf_obligation_auto_create": True,
                }
            )
            if self.perf_obligation_id:
                vals.update(
                    {
                        "perf_obligation_id": self.perf_obligation_id.id,
                    }
                )
                # we need to disconnect sale order line from the performance obligation
                # before we connect the contract line
                self.perf_obligation_id = False
        return vals
