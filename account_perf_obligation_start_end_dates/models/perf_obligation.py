# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    recognition_at_date_method = fields.Selection(
        selection_add=[
            ("daily", "Daily Pro-Rata"),
        ],
    )
    start_date = fields.Date()
    end_date = fields.Date()
    is_start_date_required = fields.Boolean(
        compute="_compute_is_date_required",
    )
    is_end_date_required = fields.Boolean(
        compute="_compute_is_date_required",
    )

    @api.depends("recognition_at_date_method")
    def _compute_is_date_required(self):
        for rec in self:
            method = rec.recognition_at_date_method
            rec.is_start_date_required = method == "daily"
            rec.is_end_date_required = method == "daily"

    @api.constrains("start_date", "end_date")
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date > rec.end_date:
                raise ValidationError(
                    _(
                        "The start date must be before or equal to "
                        "the end date on performance obligation %(name)s.",
                        name=rec.display_name,
                    )
                )

    @api.constrains("recognition_at_date_method", "start_date", "end_date")
    def _check_recognition_method_dates(self):
        for rec in self:
            if not rec.is_start_date_required and not rec.is_end_date_required:
                continue
            if (rec.is_start_date_required and not rec.start_date) or (
                rec.is_end_date_required and not rec.end_date
            ):
                raise ValidationError(
                    _(
                        "Start and end dates are required when the daily "
                        "pro-rata recognition method is selected "
                        "on performance obligation %(name)s.",
                        name=rec.display_name,
                    )
                )

    def _compute_amount_to_recognize_daily(self, date):
        """Daily pro-rata recognition method.

        Computes the amount to recognize based on the number of calendar
        days elapsed from ``start_date`` (inclusive) to ``date`` (inclusive),
        over the total number of days of the period.

        Rounding strategy: each intermediate amount is rounded using the
        currency's decimal precision. The last day always returns exactly
        ``total_amount`` to avoid any residual rounding difference.
        """
        self.ensure_one()
        start_date = self.start_date
        end_date = self.end_date

        if date < start_date:
            return 0.0
        if date >= end_date:
            return self.total_amount

        precision = self.currency_id.decimal_places
        total_days = (end_date - start_date).days + 1
        elapsed_days = (date - start_date).days + 1
        daily_amount = self.total_amount / total_days
        amount = float_round(daily_amount * elapsed_days, precision_digits=precision)
        # Safety cap: never exceed total
        return min(amount, self.total_amount)
