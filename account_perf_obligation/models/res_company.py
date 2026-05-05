# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    # Income recognition
    po_income_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Income Recognition Journal",
    )
    po_income_pl_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Recognition P&L Account",
    )
    po_income_debit_bs_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Accrual BS Account",
        help="Balance sheet account for accrued income.",
    )
    po_income_credit_bs_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Income Deferral BS Account",
        help="Balance sheet account for deferred income.",
    )

    # Expense recognition
    po_expense_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Expense Recognition Journal",
    )
    po_expense_pl_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Recognition P&L Account",
    )
    po_expense_debit_bs_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Deferral BS Account",
        help="Balance sheet account for deferred expense.",
    )
    po_expense_credit_bs_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Expense Accrual BS Account",
        help="Balance sheet account for accrued expense.",
    )
