# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero, float_round


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    recognition_at_date_method = fields.Selection(
        selection_add=[
            ("delivered", "Delivered Amount + Projected Balance"),
        ],
    )
    delivered_amount = fields.Monetary(
        string="Delivered Amount to Recognize",
        copy=False,
        tracking=True,
        help="Cumulative amount that is known to be earned and must be "
        "recognized as soon as possible, without being spread over a period. "
        "It can never exceed the total amount. The remaining balance (total "
        "amount minus delivered amount) is only projected, with draft "
        "entries, until the end date.",
    )
    recognition_lock_date = fields.Date(
        copy=False,
        readonly=True,
        tracking=True,
        help="Recognition entries up to this date have been posted (or "
        "scheduled for posting) and are frozen. It is updated each time the "
        "recognition entries are posted. The projected balance is spread "
        "between the day after this date and the end date.",
    )

    # ------------------------------------------------------------------
    # Dates / constraints
    # ------------------------------------------------------------------

    @api.model
    def _get_recognition_methods_requiring_end_date(self):
        return super()._get_recognition_methods_requiring_end_date() + ["delivered"]

    @api.constrains("recognition_at_date_method", "start_date", "end_date")
    def _check_recognition_method_dates(self):
        # The end date is required in the form, but it cannot always be
        # computed when the obligation is created automatically: it is then
        # filled in manually, so the constraint does not apply to this method.
        delivered = self.filtered(
            lambda rec: rec.recognition_at_date_method == "delivered"
        )
        return super(PerfObligation, self - delivered)._check_recognition_method_dates()

    @api.constrains("delivered_amount", "total_amount", "recognition_at_date_method")
    def _check_delivered_amount(self):
        for rec in self:
            if rec.recognition_at_date_method != "delivered":
                continue
            rounding = rec.currency_id.rounding
            amount = rec.delivered_amount
            total = rec.total_amount
            if float_is_zero(amount, precision_rounding=rounding):
                continue
            if float_compare(amount, 0, precision_rounding=rounding) != float_compare(
                total, 0, precision_rounding=rounding
            ):
                raise ValidationError(
                    _(
                        "The delivered amount must have the same sign as the "
                        "total amount on performance obligation %(name)s.",
                        name=rec.display_name,
                    )
                )
            if float_compare(abs(amount), abs(total), precision_rounding=rounding) > 0:
                raise ValidationError(
                    _(
                        "The delivered amount (%(amount)s) cannot exceed the "
                        "total amount (%(total)s) on performance obligation "
                        "%(name)s.",
                        amount=amount,
                        total=total,
                        name=rec.display_name,
                    )
                )

    def write(self, vals):
        # The total amount can be lowered automatically (source removed or
        # cancelled): keep the delivered amount within the total amount
        # instead of raising in the constraint.
        if "total_amount" in vals and "delivered_amount" not in vals:
            new_total = vals["total_amount"]
            clamped = self.browse()
            for rec in self:
                if (
                    rec.recognition_at_date_method == "delivered"
                    and float_compare(
                        abs(rec.delivered_amount),
                        abs(new_total),
                        precision_rounding=rec.currency_id.rounding,
                    )
                    > 0
                ):
                    clamped |= rec
                    new_delivered = (
                        new_total if rec.delivered_amount * new_total > 0 else 0.0
                    )
                    super(PerfObligation, rec).write(
                        dict(vals, delivered_amount=new_delivered)
                    )
            return super(PerfObligation, self - clamped).write(vals)
        return super().write(vals)

    @api.model
    def _get_recognition_trigger_fields(self):
        return super()._get_recognition_trigger_fields() + ["delivered_amount"]

    # ------------------------------------------------------------------
    # Recognition at date
    # ------------------------------------------------------------------

    def _get_recognized_balance(self, date):
        """Amount (positive for the obligation's sign convention) already
        booked, draft or posted, on P&L accounts up to *date*."""
        self.ensure_one()
        balance = self._get_income_or_expense_balance(date)
        return -balance if self.perf_type == "income" else balance

    def _get_delivered_projection_start(self):
        """First day of the period over which the balance is projected."""
        self.ensure_one()
        if self.recognition_lock_date:
            return self.recognition_lock_date + relativedelta(days=1)
        return self.start_date or fields.Date.context_today(self).replace(day=1)

    def _compute_amount_to_recognize_delivered(self, date):
        """Delivered amount + projected balance recognition method.

        Cumulative amount to recognize at *date*:

        * up to the lock date: what is already booked (frozen);
        * without end date: the delivered amount only, as the remaining
          balance cannot be projected;
        * from the end date: the total amount;
        * otherwise: the delivered amount plus the remaining balance
          (total - delivered) spread daily between the day after the lock
          date and the end date.
        """
        self.ensure_one()
        total = self.total_amount
        lock = self.recognition_lock_date
        if lock and date <= lock:
            return self._get_recognized_balance(date)
        if not self.end_date:
            return self.delivered_amount
        if date >= self.end_date:
            return total
        start = self._get_delivered_projection_start()
        total_days = (self.end_date - start).days + 1
        if total_days <= 0:
            return total
        elapsed = min(max((date - start).days + 1, 0), total_days)
        delivered = self.delivered_amount
        amount = float_round(
            delivered + (total - delivered) * elapsed / total_days,
            precision_digits=self.currency_id.decimal_places,
        )
        if total >= 0:
            return min(max(amount, delivered), total)
        return max(min(amount, delivered), total)

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    def _get_schedule_dates(self):
        """Last day of each month from the projection start to the end date."""
        self.ensure_one()
        if self.recognition_at_date_method != "delivered":
            return super()._get_schedule_dates()
        start = self._get_delivered_projection_start()
        last = max(self.end_date, start) + relativedelta(day=31)
        current = start + relativedelta(day=31)
        dates = []
        while current <= last:
            dates.append(current)
            current += relativedelta(months=1, day=31)
        return dates

    # ------------------------------------------------------------------
    # Posting
    # ------------------------------------------------------------------

    def _lock_recognition_up_to(self, date):
        """Recognize the delivered amount at *date*, freeze the obligation up
        to *date* and rebuild the projection of the remaining balance.

        Called just before the draft recognition entries dated on or before
        *date* are marked for posting: once the projection drafts are
        replaced, the only draft entry left on or before *date* is the one
        recognizing the delivered amount, so nothing more than the delivered
        amount can be posted.
        """
        selection = dict(self._fields["perf_type"]._description_selection(self.env))
        for po in self:
            lock = po.recognition_lock_date
            if lock and date <= lock:
                continue
            po = po.with_context(perf_obligation_in_regeneration=True)
            po._delete_draft_schedule_moves()
            po._recognize(
                amount_to_recognize=po.delivered_amount,
                date=date,
                description=_(
                    "%(type)s recognition %(date)s",
                    type=selection.get(po.perf_type, po.perf_type),
                    date=date,
                ),
            )
            po.recognition_lock_date = date
            po._regenerate_schedule()

    @api.model
    def _post_recognition_moves(self, date, obligations=None, companies=None):
        if companies is None:
            companies = obligations.company_id if obligations else self.env.companies
        if obligations is None:
            delivered = self.search(
                [
                    ("recognition_at_date_method", "=", "delivered"),
                    ("company_id", "in", companies.ids),
                ]
            )
        else:
            delivered = obligations.filtered(
                lambda po: po.recognition_at_date_method == "delivered"
            )
        delivered._lock_recognition_up_to(date)
        return super()._post_recognition_moves(
            date, obligations=obligations, companies=companies
        )
