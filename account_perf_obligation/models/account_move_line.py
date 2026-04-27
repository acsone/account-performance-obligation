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
