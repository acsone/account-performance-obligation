# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        # sudo: the user confirming the order may have no access to
        # performance obligations
        self.sudo()._start_perf_obligations()
        return res

    def _start_perf_obligations(self):
        """Start the performance obligations whose service is delivered from the
        order confirmation (see
        ``sale.order.line._is_perf_obligation_started_on_confirmation``)."""
        for order in self:
            for line in order.order_line:
                if not line._is_perf_obligation_started_on_confirmation():
                    continue
                obligation = line.perf_obligation_id.sudo()
                if not obligation.not_in_service:
                    continue
                obligation._start()
                obligation._message_log(
                    body=_(
                        "Put in service from sale order confirmation (sale order"
                        " %(order)s).",
                        order=order.name,
                    )
                )
