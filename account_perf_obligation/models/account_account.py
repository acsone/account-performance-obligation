# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountAccount(models.Model):
    _inherit = "account.account"

    def _performance_obligation_allowed(self):
        """Check if this account can be linked to a performance obligation."""
        self.ensure_one()
        return self.internal_group in (
            "income",
            "expense",
        ) or self.account_type in (
            "asset_current",
            "liability_current",
        )
