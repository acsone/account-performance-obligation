# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        index=True,
        check_company=True,
        ondelete="restrict",
    )

    @api.constrains("perf_obligation_id", "account_id")
    def _check_perf_obligation_account(self):
        for line in self:
            if not line.perf_obligation_id:
                continue
            account = line.account_id
            if account.internal_group in (
                "income",
                "expense",
            ) or account.account_type in (
                "asset_current",
                "liability_current",
            ):
                continue
            raise ValidationError(
                _(
                    "Account '%(account)s' cannot be used with a performance "
                    "obligation. Only Income, Expense, Current Assets and "
                    "Current Liabilities accounts are allowed.",
                    account=account.display_name,
                )
            )

    def _get_perf_obligations_to_mark(self):
        if self.env.context.get("perf_obligation_in_regeneration"):
            return self.env["perf.obligation"]
        return self.perf_obligation_id

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._get_perf_obligations_to_mark()._mark_for_regeneration()
        return lines

    def write(self, vals):
        before = self._get_perf_obligations_to_mark()
        res = super().write(vals)
        after = self._get_perf_obligations_to_mark()
        (before | after)._mark_for_regeneration()
        return res

    def unlink(self):
        obligations = self._get_perf_obligations_to_mark()
        res = super().unlink()
        obligations.exists()._mark_for_regeneration()
        return res
