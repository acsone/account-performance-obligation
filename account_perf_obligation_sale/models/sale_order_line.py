# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from dateutil.relativedelta import relativedelta

from odoo import _, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _name = "sale.order.line"
    _inherit = ["sale.order.line", "perf.obligation.source.mixin"]

    def _create_or_update_perf_obligation(self):
        """Create or update a performance obligation for this line if applicable.

        Skips lines whose product does not have automatic creation enabled.
        """
        self.ensure_one()
        product = self.product_id
        if not product.perf_obligation_sale_auto_create:
            return None
        if not product.perf_obligation_sale_recognition_method:
            return None
        # Duplicate guard: update existing obligation instead of creating a new one
        if self.perf_obligation_id:
            self._update_perf_obligation(self.perf_obligation_id)
            return self.perf_obligation_id
        vals = self._prepare_perf_obligation_vals()
        obligation = self.env["perf.obligation"].sudo().create(vals)
        self.perf_obligation_id = obligation
        return obligation

    def _update_perf_obligation(self, obligation):
        """Update an existing performance obligation with current line data.

        Called on re-confirmation of a sale order. Brings dates, total amount
        and any other computed fields back in sync with the current SOL state,
        as if the obligation had just been created from scratch.
        """
        self.ensure_one()
        obligation._ensure_sole_source(self)
        vals = self._prepare_perf_obligation_vals()
        obligation.sudo().write(vals)
        obligation.sudo()._message_log(
            body=_(
                "Values updated on re-confirmation of sale order %(order)s.",
                order=self.order_id.name,
            )
        )

    def _prepare_perf_obligation_vals(self):
        """Return the values dict for the performance obligation to create."""
        self.ensure_one()
        start_date, end_date = self._get_perf_obligation_dates()
        vals = {
            "perf_type": "income",
            "total_amount": self._get_obligation_amount(),
            "start_date": start_date,
            "end_date": end_date,
            "recognition_at_date_method": "daily",
            "description": _(
                "Auto-created from sale order %(order)s - %(product)s",
                order=self.order_id.name,
                product=self.product_id.display_name,
            ),
        }
        income_account = self._get_perf_obligation_income_account()
        if income_account:
            vals["pl_account_id"] = income_account.id
        return vals

    def _get_perf_obligation_income_account(self):
        """Return the income account to set on the performance obligation."""
        self.ensure_one()
        product = self.product_id
        account = product.product_tmpl_id.get_product_accounts(
            fiscal_pos=self.order_id.fiscal_position_id
        ).get("income")
        return account

    def _get_perf_obligation_dates(self):
        """Return (start_date, end_date) for the performance obligation.

        - 'at_once': start = end = order confirmation date
        - 'months': start = confirmation date,
                    end = start + N calendar months
        - 'days':   start = confirmation date,
                    end = start + N days
        """
        self.ensure_one()
        product = self.product_id
        method = product.perf_obligation_sale_recognition_method
        confirmation_date = self.order_id.date_order.date()

        if method == "at_once":
            return confirmation_date, confirmation_date

        if method == "months":
            months = product.perf_obligation_sale_months_duration
            end_date = confirmation_date + relativedelta(months=months)
            return confirmation_date, end_date

        if method == "days":
            days = product.perf_obligation_sale_days_duration
            end_date = confirmation_date + relativedelta(days=days)
            return confirmation_date, end_date

        raise ValidationError(
            _(
                "Unknown performance obligation recognition method '%(method)s' "
                "on product '%(product)s'.",
                method=method,
                product=product.display_name,
            )
        )

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)
        if self.perf_obligation_id:
            vals["perf_obligation_id"] = self.perf_obligation_id.id
        return vals

    def _get_obligation_amount(self):
        return self.price_subtotal
