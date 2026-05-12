# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    contract_line_id = fields.Many2one(
        comodel_name="contract.line",
        string="Contract Line",
        index=True,
        copy=False,
        ondelete="restrict",
        help="Contract line from which this performance obligation "
        "was automatically created.",
    )
