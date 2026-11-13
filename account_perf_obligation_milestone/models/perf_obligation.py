# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

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
            key=lambda m: (m.date, m.id)
        )

    def _check_milestones(self):
        """Milestone amounts are cumulative: they must have the same sign as
        the total amount and not exceed it, as required by ``_recognize``.
        They may decrease over time (income can be de-recognized)."""
        for po in self:
            currency = po.currency_id
            sign = -1 if po.total_amount < 0 else 1
            abs_total = abs(po.total_amount)
            for milestone in po._get_effective_milestones():
                value = sign * milestone.amount
                if (
                    currency.compare_amounts(value, 0) < 0
                    or currency.compare_amounts(value, abs_total) > 0
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

    def _compute_amount_to_recognize_daily(self, date):
        """Daily pro-rata recognition, linear between milestones.

        Without milestone, this is the plain daily pro-rata. Otherwise the
        cumulative amount is a piecewise linear function going through
        (day before ``start_date``, 0), each milestone (end of its date,
        its amount) and (``end_date``, total amount). Day indexes follow the
        daily method: ``start_date`` is day 1.

        Amounts are clamped to [0, total], so that a total amount changed
        after the milestones were entered cannot make the recognition fail.
        Amounts may decrease from one milestone to the next.
        """
        self.ensure_one()
        milestones = self._get_effective_milestones()
        if not milestones:
            return super()._compute_amount_to_recognize_daily(date)
        start_date = self.start_date
        if date < start_date:
            return 0.0
        if date >= self.end_date:
            return self.total_amount

        sign = -1 if self.total_amount < 0 else 1
        abs_total = abs(self.total_amount)
        total_days = (self.end_date - start_date).days + 1
        elapsed_days = (date - start_date).days + 1

        targets = {0: 0.0, total_days: abs_total}
        for milestone in milestones:
            day = (milestone.date - start_date).days + 1
            if day >= total_days:
                # the end of the period always reaches the total amount
                continue
            targets[day] = max(0.0, min(sign * milestone.amount, abs_total))
        days = sorted(targets)
        next_day = next(day for day in days if day >= elapsed_days)
        prev_day = days[days.index(next_day) - 1]
        prev_amount, next_amount = targets[prev_day], targets[next_day]
        amount = prev_amount + (next_amount - prev_amount) * (
            elapsed_days - prev_day
        ) / (next_day - prev_day)
        return float_round(
            sign * amount, precision_digits=self.currency_id.decimal_places
        )

    def _get_schedule_dates(self):
        """Also generate a recognition entry at each milestone date, so that
        the milestone amount is exactly reached on the milestone date and not
        only at the next month end."""
        dates = super()._get_schedule_dates()
        milestones = self._get_effective_milestones()
        if milestones:
            last_posted = self._get_last_posted_recognition_date()
            # periods already covered by a posted entry are never regenerated
            milestone_dates = {
                m.date for m in milestones if not last_posted or m.date > last_posted
            }
            dates = sorted(set(dates) | milestone_dates)
        return dates
