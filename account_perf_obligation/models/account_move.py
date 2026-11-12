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
            done = move.line_ids.perf_obligation_id.filtered(
                lambda po: po.state == "done"
            )
            if done:
                raise UserError(
                    _(
                        "Cannot post %(move)s: performance obligation "
                        "%(obligation)s is done. There should not be draft "
                        "moves linked to a done performance obligation. "
                        "Please report the issue.",
                        move=move.display_name,
                        obligation=", ".join(done.mapped("display_name")),
                    )
                )
        for move in reco_moves:
            move.line_ids.perf_obligation_id._check_blocking_draft_moves(move.date)
        res = super()._post(soft=soft)
        # Covers both recognition entries and invoices (last movement).
        po_moves.line_ids.perf_obligation_id._auto_set_done()
        return res
