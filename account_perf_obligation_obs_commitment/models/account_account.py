# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _performance_obligation_allowed(self):
        """Allow off-balance sheet accounts for commitments."""
        self.ensure_one()
        if self.account_type == "off_balance":
            return True
        return super()._performance_obligation_allowed()
