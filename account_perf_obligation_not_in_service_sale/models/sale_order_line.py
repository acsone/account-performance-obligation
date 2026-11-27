# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _prepare_perf_obligation_vals(self):
        vals = super()._prepare_perf_obligation_vals()
        if not self.perf_obligation_id:
            vals["not_in_service"] = True
        return vals

    def _is_perf_obligation_started_on_confirmation(self):
        """Return True if the obligation of this line starts at the order
        confirmation, i.e. when the service is delivered from the confirmation
        (at once / over several months / over several days).

        Override to add other recognition methods that start at another time
        (the obligation then stays flagged as not in service until the service really
        starts).
        """
        self.ensure_one()
        return bool(
            self.perf_obligation_id
            and self.product_id.perf_obligation_sale_recognition_method
            in ("at_once", "months", "days")
        )
