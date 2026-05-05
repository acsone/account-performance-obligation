# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    recognition_cap_enabled = fields.Boolean(
        string="Limit Maximum Amount to Recognize",
        default=False,
        copy=False,
        tracking=True,
        help="When enabled, the recognized amount on this obligation will "
        "never exceed the configured cap (in absolute terms), even if the "
        "recognition method or linked invoices/bills would otherwise "
        "recognize more.",
    )
    recognition_cap_amount = fields.Monetary(
        string="Maximum Amount Allowed for Recognition",
        copy=False,
        tracking=True,
        help="Maximum cumulative amount that can be recognized for this "
        "obligation. Must have the same sign as the total amount and its "
        "absolute value cannot exceed that of the total amount.",
    )

    @api.constrains(
        "recognition_cap_enabled",
        "recognition_cap_amount",
        "total_amount",
    )
    def _check_recognition_cap(self):
        for rec in self:
            if not rec.recognition_cap_enabled:
                continue
            precision = rec.currency_id.rounding
            cap_sign = float_compare(
                rec.recognition_cap_amount, 0, precision_rounding=precision
            )
            total_sign = float_compare(
                rec.total_amount, 0, precision_rounding=precision
            )
            # Cap must be zero or carry the same sign as total_amount.
            if cap_sign != 0 and cap_sign != total_sign:
                raise ValidationError(
                    _(
                        "The recognition cap must have the same sign as "
                        "the total amount on performance obligation %(name)s.",
                        name=rec.display_name,
                    )
                )
            # |cap| must not exceed |total_amount|.
            if (
                float_compare(
                    abs(rec.recognition_cap_amount),
                    abs(rec.total_amount),
                    precision_rounding=precision,
                )
                > 0
            ):
                raise ValidationError(
                    _(
                        "The recognition cap (%(cap)s) cannot exceed "
                        "the total amount (%(total)s) on performance "
                        "obligation %(name)s.",
                        cap=rec.recognition_cap_amount,
                        total=rec.total_amount,
                        name=rec.display_name,
                    )
                )

    @api.model
    def _get_recognition_trigger_fields(self):
        return super()._get_recognition_trigger_fields() + [
            "recognition_cap_enabled",
            "recognition_cap_amount",
        ]

    def _apply_recognition_cap(self, amount):
        """Return the capped amount, respecting the obligation's sign.

        For positive obligations (total_amount > 0):
            returns min(amount, cap)  — prevents amount from going too high.

        For negative obligations (total_amount < 0):
            returns max(amount, cap)  — prevents amount from going too
            negative (i.e. exceeding the cap in absolute terms).

        When the cap is disabled the amount is returned unchanged.
        """
        self.ensure_one()
        if self.recognition_cap_enabled:
            if self.total_amount >= 0:
                return min(amount, self.recognition_cap_amount)
            else:
                return max(amount, self.recognition_cap_amount)
        return amount

    def _compute_amount_to_recognize_at_date(self, date):
        """Apply the recognition cap on top of the configured method.

        When the parent computation would yield an amount whose absolute
        value exceeds the cap, the cap is returned instead. As a
        consequence:

        - the schedule entry that would first cross the cap is reduced
          to land exactly on the cap;
        - all subsequent schedule dates produce zero variation in
          ``_recognize`` and therefore no journal entry is generated;
        - if the cap is set below the already-recognized amount (in
          absolute terms), the variation is reversed and a
          "de-recognition" entry is generated to bring the cumulative
          recognized amount back to the cap.
        """
        amount = super()._compute_amount_to_recognize_at_date(date)
        return self._apply_recognition_cap(amount)

    def _recognize(self, amount_to_recognize, date, description):
        """Reject manual recognitions whose absolute value exceeds the cap.

        The schedule generator already passes capped amounts (via
        ``_compute_amount_to_recognize_at_date``), so this guard
        only fires on the manual wizard path.
        """
        self.ensure_one()
        if self.recognition_cap_enabled:
            precision = self.currency_id.rounding
            if (
                float_compare(
                    abs(amount_to_recognize),
                    abs(self.recognition_cap_amount),
                    precision_rounding=precision,
                )
                > 0
            ):
                raise ValidationError(
                    _(
                        "The amount to recognize (%(amount)s) cannot "
                        "exceed the recognition cap (%(cap)s) on "
                        "performance obligation %(name)s.",
                        amount=amount_to_recognize,
                        cap=self.recognition_cap_amount,
                        name=self.display_name,
                    )
                )
        return super()._recognize(amount_to_recognize, date, description)
