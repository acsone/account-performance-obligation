# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        perf_obligation_model = self.env["perf.obligation"]
        for move in self:
            reco_journals = (
                perf_obligation_model._get_recognition_journals_for_companies(
                    move.company_id
                )
            )
            if move.journal_id in reco_journals:
                blocked_pos = move.line_ids.perf_obligation_id.filtered(
                    "not_in_service"
                )
                if blocked_pos:
                    raise UserError(
                        _(
                            "Cannot post recognition entry %(move)s: performance "
                            "obligation(s) %(obligations)s are marked as Not in "
                            "Service.",
                            move=move.display_name,
                            obligations=", ".join(blocked_pos.mapped("display_name")),
                        )
                    )
        return super().action_post()
