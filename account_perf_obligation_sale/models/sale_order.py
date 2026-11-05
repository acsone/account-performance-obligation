# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.tools import format_amount


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
        action = {
            "type": "ir.actions.act_window",
            "name": _("Performance Obligations"),
            "res_model": "perf.obligation",
            "view_mode": "list,form",
            "domain": [("id", "in", obligation_ids)],
            "context": {"create": False},
        }
        if len(obligation_ids) == 1:
            action.update({"view_mode": "form", "res_id": obligation_ids[0]})
        return action

    def action_confirm(self):
        res = super().action_confirm()
        self._create_perf_obligations()
        self._start_perf_obligations()
        return res

    def _start_perf_obligations(self):
        """Start the performance obligations whose service is delivered from the
        order confirmation (see
        ``sale.order.line._is_perf_obligation_started_on_confirmation``)."""
        for line in self.order_line:
            if not line._is_perf_obligation_started_on_confirmation():
                continue
            obligation = line.perf_obligation_id.sudo()
            if obligation.state != "draft":
                continue
            obligation._start()
            obligation._message_log(
                body=_(
                    "Started from sale order confirmation (sale order %(order)s).",
                    order=line.order_id.name,
                )
            )

    def _create_perf_obligations(self):
        """Create performance obligations for qualifying sale order lines."""
        for order in self:
            for line in order.order_line:
                line._create_or_update_perf_obligation()

    def _action_cancel(self):
        res = super()._action_cancel()
        self._cancel_perf_obligations()
        return res

    def _cancel_perf_obligations(self):
        """Update performance obligations on sale order cancellation."""
        for order in self:
            for line in order.order_line:
                if line.perf_obligation_id:
                    obligation = line.perf_obligation_id
                    obligation._ensure_sole_source(line)
                    invoiced_amount = obligation._get_invoiced_amount()
                    obligation._update_total_amount(
                        invoiced_amount,
                        _(
                            "Total amount updated to already invoiced amount %(amount)s"
                            " on cancellation of %(cancelled_source)s.",
                            amount=format_amount(
                                obligation.env,
                                invoiced_amount,
                                obligation.currency_id
                                or obligation.env.company.currency_id,
                            ),
                            cancelled_source=_("sale order %s") % order.name,
                        ),
                    )
