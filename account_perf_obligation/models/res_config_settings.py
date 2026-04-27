# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    po_income_journal_id = fields.Many2one(
        related="company_id.po_income_journal_id",
        readonly=False,
    )
    po_income_pl_account_id = fields.Many2one(
        related="company_id.po_income_pl_account_id",
        readonly=False,
    )
    po_income_debit_bs_account_id = fields.Many2one(
        related="company_id.po_income_debit_bs_account_id",
        readonly=False,
    )
    po_income_credit_bs_account_id = fields.Many2one(
        related="company_id.po_income_credit_bs_account_id",
        readonly=False,
    )
    po_expense_journal_id = fields.Many2one(
        related="company_id.po_expense_journal_id",
        readonly=False,
    )
    po_expense_pl_account_id = fields.Many2one(
        related="company_id.po_expense_pl_account_id",
        readonly=False,
    )
    po_expense_debit_bs_account_id = fields.Many2one(
        related="company_id.po_expense_debit_bs_account_id",
        readonly=False,
    )
    po_expense_credit_bs_account_id = fields.Many2one(
        related="company_id.po_expense_credit_bs_account_id",
        readonly=False,
    )
