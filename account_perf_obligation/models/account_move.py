# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    perf_obligation_schedule_move = fields.Boolean(
        copy=False,
        help="Set to True when this journal entry was automatically generated. "
        "Such entries are deleted during schedule regeneration.",
        readonly=True,
    )
