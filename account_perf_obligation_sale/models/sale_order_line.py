# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    perf_obligation_ids = fields.One2many(
        comodel_name="perf.obligation",
        inverse_name="sale_order_line_id",
        string="Performance Obligations",
    )

    def _create_perf_obligation_if_needed(self):
        """Create a performance obligation for this line if applicable.

        Skips lines whose product does not have automatic creation enabled,
        and lines for which an obligation already exists (duplicate guard).
        """
        self.ensure_one()
        product = self.product_id
        if not product.perf_obligation_auto_create:
            return None
        if not product.perf_obligation_recognition_method:
            return None
        # Duplicate guard
        if self.perf_obligation_ids:
            return self.perf_obligation_ids[0]
        vals = self._prepare_perf_obligation_vals()
        return self.env["perf.obligation"].create(vals)

    def _prepare_perf_obligation_vals(self):
        """Return the values dict for the performance obligation to create."""
        self.ensure_one()
        start_date, end_date = self._get_perf_obligation_dates()
        return {
            "perf_type": "income",
            "total_amount": self.price_subtotal,
            "start_date": start_date,
            "end_date": end_date,
            "sale_order_line_id": self.id,
            "recognition_at_date_method": "daily",
            "description": _(
                "Auto-created from sale order %(order)s - %(product)s",
                order=self.order_id.name,
                product=self.product_id.display_name,
            ),
        }

    def _get_perf_obligation_dates(self):
        """Return (start_date, end_date) for the performance obligation.

        - 'at_once': start = end = order confirmation date
        - 'months': start = confirmation date,
                    end = start + N months
        """
        self.ensure_one()
        product = self.product_id
        method = product.perf_obligation_recognition_method
        confirmation_date = self.order_id.date_order.date()

        if method == "at_once":
            return confirmation_date, confirmation_date

        if method == "months":
            months = product.perf_obligation_months_duration
            end_date = confirmation_date + relativedelta(months=months)
            return confirmation_date, end_date

        # Fallback: at_once (should not happen given validation constraints)
        return confirmation_date, confirmation_date

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)
        if self.perf_obligation_ids:
            vals["perf_obligation_id"] = self.perf_obligation_ids[0].id
        return vals
