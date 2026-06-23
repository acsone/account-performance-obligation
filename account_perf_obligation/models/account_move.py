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

    def _post(self, soft=True):
        reco_journals = self.env[
            "perf.obligation"
        ]._get_recognition_journals_for_companies(self.company_id)
        reco_moves = self.filtered(
            lambda m: m.line_ids.perf_obligation_id and m.journal_id in reco_journals
        )
        for move in reco_moves:
            move.line_ids.perf_obligation_id._check_blocking_draft_moves(move.date)
        return super()._post(soft=soft)
