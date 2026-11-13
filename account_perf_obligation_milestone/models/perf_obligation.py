# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import timedelta

from odoo import _, fields, models
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
        dated outside the recognition period are ignored.
        """
        self.ensure_one()
        if self.recognition_at_date_method != "daily":
            return self.milestone_ids.browse()
        return self.milestone_ids.filtered(lambda m: not m.is_out_of_period).sorted(
            "date"
        )

    def _check_milestones(self):
        """Milestone amounts are cumulative: they must have the same sign as
        the total amount and not exceed it, as required by ``_recognize``.
        They may decrease over time (income can be de-recognized)."""
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

    def _get_milestone_interval(self, date):
        """Return the two points ``((date1, amount1), (date2, amount2))``
        surrounding ``date``, with ``date1 < date <= date2``.

        Points are (date, cumulative amount to recognize at the end of that
        date): the day before ``start_date`` (0), the milestones, and
        ``end_date`` (total amount). Milestone amounts are clamped between 0
        and the total, so that a total amount changed after the milestones
        were entered cannot make the recognition fail.

        ``date`` must be between ``start_date`` and ``end_date``.
        """
        self.ensure_one()
        low, high = sorted((0.0, self.total_amount))
        points = [(self.start_date - timedelta(days=1), 0.0)]
        points += [
            (milestone.date, min(max(milestone.amount, low), high))
            for milestone in self._get_effective_milestones()
            # the end of the period always reaches the total amount
            if milestone.date < self.end_date
        ]
        points.append((self.end_date, self.total_amount))
        previous = points[0]
        for point in points[1:]:
            if date <= point[0]:
                return previous, point
            previous = point

    def _compute_amount_to_recognize_daily(self, date):
        """Daily pro-rata recognition, linear between milestones.

        Without milestone, this is the plain daily pro-rata.
        """
        self.ensure_one()
        if not self._get_effective_milestones():
            return super()._compute_amount_to_recognize_daily(date)
        if date < self.start_date:
            return 0.0
        if date >= self.end_date:
            return self.total_amount
        (date1, amount1), (date2, amount2) = self._get_milestone_interval(date)
        amount = (
            amount1 + (amount2 - amount1) * (date - date1).days / (date2 - date1).days
        )
        return float_round(amount, precision_digits=self.currency_id.decimal_places)
