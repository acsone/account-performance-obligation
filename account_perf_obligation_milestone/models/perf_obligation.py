# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    milestone_ids = fields.One2many(
        comodel_name="perf.obligation.milestone",
        inverse_name="perf_obligation_id",
        string="Milestones",
    )

    def _get_effective_milestones(self):
        """Return the milestones taken into account by the recognition,
        sorted by date.

        Milestones are only used by the daily pro-rata method, and those
        dated outside the recognition period are ignored (start date included, end
        date excluded).
        """
        self.ensure_one()
        if self.recognition_at_date_method != "daily":
            return self.milestone_ids.browse()
        return self.milestone_ids.filtered(lambda m: not m.is_ignored).sorted("date")

    @api.constrains(
        "total_amount", "start_date", "end_date", "recognition_at_date_method"
    )
    def _check_milestones(self):
        """Milestone amounts are cumulative: they must have the same sign as
        the total amount and not exceed it, as required by ``_recognize``.
        They may decrease over time (income can be de-recognized).
        Ignored milestones are not validated. They are validated again if they become
        effective (change of dates or method).
        """
        for po in self:
            currency = po.currency_id
            low, high = sorted((0.0, po.total_amount))
            for milestone in po._get_effective_milestones():
                if (
                    currency.compare_amounts(milestone.amount, low) < 0
                    or currency.compare_amounts(milestone.amount, high) > 0
                ):
                    raise ValidationError(
                        _(
                            "Milestone amounts of performance obligation "
                            "%(name)s are cumulative: they must have the same "
                            "sign as the total amount and not exceed it "
                            "(milestone of %(date)s).",
                            name=po.display_name,
                            date=milestone.date,
                        )
                    )

    def _get_milestone_intervals(self):
        """Yield the segments of the recognition curve, in date order.

        A segment is ``((date1, amount1), (date2, amount2))``: ``amount1`` is
        the cumulative amount recognized at the end of the day *before*
        ``date1``, ``amount2`` the one recognized at the end of ``date2``. The
        recognition is linear over the days ``date1`` to ``date2`` (both
        included).

        The segments are contiguous: they go from ``start_date`` (after an
        amount of 0) to ``end_date`` (total amount), through each effective
        milestone.
        """
        self.ensure_one()
        date1, amount1 = self.start_date, 0.0
        for milestone in self._get_effective_milestones():
            yield (date1, amount1), (milestone.date, milestone.amount)
            date1, amount1 = milestone.date + timedelta(days=1), milestone.amount
        yield (date1, amount1), (self.end_date, self.total_amount)

    def _compute_amount_to_recognize_daily(self, date):
        """Daily pro-rata recognition method, linear between milestones.

        Same convention as the base method (the returned amount is the
        cumulative amount recognized at the end of ``date``, ``start_date``
        being day 1), but the days are counted within the segment of the
        recognition curve that contains ``date``, see
        ``_get_milestone_intervals``.

        Without effective milestone, this is the plain daily pro-rata.
        """
        self.ensure_one()
        if not self._get_effective_milestones():
            return super()._compute_amount_to_recognize_daily(date)
        if date < self.start_date:
            return 0.0
        if date >= self.end_date:
            return self.total_amount
        # the segments cover every day of the period: there is always one
        for (date1, amount1), (date2, amount2) in self._get_milestone_intervals():
            if date1 <= date <= date2:
                amount = amount1 + (amount2 - amount1) * ((date - date1).days + 1) / (
                    (date2 - date1).days + 1
                )
                return float_round(
                    amount, precision_digits=self.currency_id.decimal_places
                )
        # Unreachable: the segments cover every day from start_date to end_date.
        raise AssertionError("date not covered by milestone intervals")
