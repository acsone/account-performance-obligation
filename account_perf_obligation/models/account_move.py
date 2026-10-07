# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


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
        po_moves = self.filtered(lambda m: m.line_ids.perf_obligation_id)
        reco_moves = po_moves.filtered(lambda m: m.journal_id in reco_journals)
        for move in po_moves:
            for obligation in move.line_ids.perf_obligation_id:
                if obligation.state == "done":
                    raise UserError(
                        _(
                            "Cannot post %(move)s: performance obligation "
                            "%(obligation)s is done. Set it back to 'In Progress' "
                            "first.",
                            move=move.display_name,
                            obligation=obligation.display_name,
                        )
                    )
                if move in reco_moves and obligation.state != "in_progress":
                    raise UserError(
                        _(
                            "Cannot post recognition entry %(move)s: performance "
                            "obligation %(obligation)s is not in progress.",
                            move=move.display_name,
                            obligation=obligation.display_name,
                        )
                    )
        for move in reco_moves:
            move.line_ids.perf_obligation_id._check_blocking_draft_moves(move.date)
        res = super()._post(soft=soft)
        # Covers both recognition entries and invoices (last movement).
        po_moves.line_ids.perf_obligation_id._auto_set_done()
        return res
