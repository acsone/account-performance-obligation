# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools.misc import format_amount


class SaleOrder(models.Model):
    _inherit = "sale.order"

    perf_obligation_count = fields.Integer(
        compute="_compute_perf_obligation_count",
        string="Performance Obligations",
        readonly=True,
    )

    @api.depends("order_line.perf_obligation_id")
    def _compute_perf_obligation_count(self):
        for order in self:
            order.perf_obligation_count = len(
                order.order_line.mapped("perf_obligation_id")
            )

    def action_view_perf_obligations(self):
        self.ensure_one()
        obligation_ids = self.order_line.mapped("perf_obligation_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Performance Obligations"),
            "res_model": "perf.obligation",
            "view_mode": "list,form",
            "domain": [("id", "in", obligation_ids)],
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
        for order in self:
            for line in order.order_line:
                obligation = line.perf_obligation_id
                if not obligation:
                    continue
                vals = self._prepare_perf_obligation_cancel_vals(line, obligation)
                obligation.write(vals)
                obligation._message_log(
                    body=_(
                        "Total amount updated to already invoiced amount %(amount)s "
                        "on cancellation of sale order %(order)s.",
                        amount=format_amount(
                            self.env,
                            vals["total_amount"],
                            obligation.currency_id or self.env.company.currency_id,
                        ),
                        order=order.name,
                    )
                )

    def _prepare_perf_obligation_cancel_vals(self, sol, obligation):
        return {
            "total_amount": sol.untaxed_amount_invoiced,
        }
