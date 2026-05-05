# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import calendar

from dateutil.relativedelta import relativedelta

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
    start_date = fields.Date(tracking=True)
    end_date = fields.Date(tracking=True)
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
        if self.total_amount > 0:
            return min(amount, self.total_amount)
        else:
            return max(amount, self.total_amount)

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    @api.depends("recognition_at_date_method", "start_date", "end_date")
    def _compute_supports_schedule(self):
        for rec in self:
            rec.supports_schedule = rec._supports_schedule()

    def _supports_schedule(self):
        """Scheduling is supported when a recognition method is configured
        and both start and end dates are set."""
        self.ensure_one()
        return (
            self._supports_recognition_at_date() and self.start_date and self.end_date
        )

    def _get_schedule_start_date(self, min_move_date=None):
        """Return the earliest date the schedule should cover.

        Does not account for posted recognition entries (handled separately
        in _get_schedule_dates via last_posted).
        """
        self.ensure_one()
        if min_move_date:
            return min(min_move_date, self.start_date)
        return self.start_date

    def _get_schedule_end_date(self, max_move_date=None):
        """Return the date until which schedule entries should be generated.

        Takes max(last move line date, end_date) so that schedule covers any
        movement posted after the obligation period.

        :param max_move_date: optional pre-computed max date of move lines
            linked to this obligation.
        """
        self.ensure_one()
        if max_move_date:
            return max(max_move_date, self.end_date)
        return self.end_date

    def _get_schedule_dates(self):
        """Return last day of each month from schedule start to schedule end.

        Schedule starts from the obligation's start date (or before if a
        movement was posted earlier), or after the last posted recognition
        entry if one exists. Schedule ends at end_date, extended to cover
        any movement posted after end_date. If a month boundary falls
        beyond, the actual schedule end date is used.
        """
        self.ensure_one()
        if not self.end_date:
            raise ValidationError(
                _(
                    "An end date is required to generate schedule entries "
                    "on performance obligation %(name)s.",
                    name=self.display_name,
                )
            )

        min_move_date, max_move_date = self._get_move_lines_date_range()
        schedule_start = self._get_schedule_start_date(min_move_date)
        schedule_end = self._get_schedule_end_date(max_move_date)

        if schedule_start > schedule_end:
            return []

        last_posted = self._get_last_posted_recognition_date()

        dates = []
        current = schedule_start.replace(day=1)
        while current <= schedule_end:
            month_end = current.replace(
                day=calendar.monthrange(current.year, current.month)[1]
            )
            # Skip months strictly before the period start
            # (but not equal, to include a start_date on the last day of a month)
            if month_end < schedule_start:
                current += relativedelta(months=1)
                continue
            # Skip months already covered by a posted recognition entry
            # (strict <=: the posted month-end itself is already recognized)
            if last_posted and month_end <= last_posted:
                current += relativedelta(months=1)
                continue
            dates.append(min(month_end, schedule_end))
            current += relativedelta(months=1)
        return dates

    @api.model
    def _get_recognition_trigger_fields(self):
        return super()._get_recognition_trigger_fields() + [
            "start_date",
            "end_date",
        ]
