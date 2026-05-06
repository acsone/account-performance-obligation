# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    perf_obligation_count = fields.Integer(
        compute="_compute_perf_obligation_count",
        string="Performance Obligations",
        readonly=True,
    )

    @api.depends("order_line.perf_obligation_ids")
    def _compute_perf_obligation_count(self):
        groups = self.env["perf.obligation"]._read_group(
            domain=[("sale_order_line_id", "in", self.mapped("order_line").ids)],
            groupby=["sale_order_line_id"],
            aggregates=["__count"],
        )
        counts = {line.id: count for line, count in groups}
        for order in self:
            order.perf_obligation_count = sum(
                counts.get(line.id, 0) for line in order.order_line
            )

    def action_view_perf_obligations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Performance Obligations"),
            "res_model": "perf.obligation",
            "view_mode": "list,form",
            "domain": [("sale_order_line_id", "in", self.order_line.ids)],
            "context": {"create": False},
        }

    def action_confirm(self):
        res = super().action_confirm()
        self._create_perf_obligations()
        return res

    def _create_perf_obligations(self):
        """Create performance obligations for qualifying sale order lines."""
        for order in self:
            for line in order.order_line:
                line._create_perf_obligation_if_needed()

    def action_cancel(self):
        self._cancel_perf_obligations()
        return super().action_cancel()

    def _cancel_perf_obligations(self):
        """Freeze performance obligations on cancellation.

        Sets total_amount to the already-invoiced amount so that:
        - if nothing was invoiced: total_amount becomes 0, no future
          recognition is generated.
        - if something was invoiced: total_amount is reduced to match
          the invoiced amount, and any excess already-recognized amount
          will be reversed on the next schedule regeneration.
        """
        obligations = self.env["perf.obligation"].search(
            [("sale_order_line_id", "in", self.order_line.ids)]
        )
        for obligation in obligations:
            obligation.write(self._prepare_perf_obligation_cancel_vals(obligation))

    def _prepare_perf_obligation_cancel_vals(self, obligation):
        sol = obligation.sale_order_line_id
        return {
            "total_amount": sol.untaxed_amount_invoiced if sol else 0.0,
        }
