# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    po_obs_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Off-Balance Sheet Journal",
    )
    po_obs_income_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Off-Balance Sheet Commitment Income Account",
        domain="[('account_type', '=', 'off_balance')]",
    )
    po_obs_expense_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Off-Balance Sheet Commitment Expense Account",
        domain="[('account_type', '=', 'off_balance')]",
    )
    po_obs_counterpart_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Off-Balance Sheet Commitment Counterpart Account",
        domain="[('account_type', '=', 'off_balance')]",
    )
