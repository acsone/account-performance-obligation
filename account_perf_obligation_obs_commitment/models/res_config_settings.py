# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    po_obs_commitment_journal_id = fields.Many2one(
        related="company_id.po_obs_commitment_journal_id",
        readonly=False,
    )
    po_obs_commitment_income_account_id = fields.Many2one(
        related="company_id.po_obs_commitment_income_account_id",
        readonly=False,
    )
    po_obs_commitment_expense_account_id = fields.Many2one(
        related="company_id.po_obs_commitment_expense_account_id",
        readonly=False,
    )
    po_obs_commitment_counterpart_account_id = fields.Many2one(
        related="company_id.po_obs_commitment_counterpart_account_id",
        readonly=False,
    )
