# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains("perf_obligation_id", "account_id")
    def _check_perf_obligation_account(self):
        """Override to also allow off_balance accounts on OBS journal entries."""
        lines_to_check = self.filtered(
            lambda line: line.account_id.account_type != "off_balance"
        )
        return super(AccountMoveLine, lines_to_check)._check_perf_obligation_account()
