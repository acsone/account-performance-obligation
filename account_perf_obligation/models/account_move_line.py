# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        index=True,
        check_company=True,
        ondelete="restrict",
    )

    @api.constrains("perf_obligation_id", "account_id")
    def _check_perf_obligation_account(self):
        for line in self:
            if not line.perf_obligation_id:
                continue
            if not line.account_id._performance_obligation_allowed():
                raise ValidationError(
                    _(
                        "Account '%(account)s' cannot be used with a performance "
                        "obligation.",
                        account=line.account_id.display_name,
                    )
                )

    @api.constrains("perf_obligation_id", "parent_state")
    def _check_no_draft_line_on_done_obligation(self):
        lines = self.filtered(
            lambda line: line.parent_state == "draft"
            and line.perf_obligation_id.state == "done"
        )
        if lines:
            raise UserError(
                _(
                    "Cannot have draft entries (%(moves)s) linked to done "
                    "performance obligation %(obligations)s. Reopen it first.",
                    moves=", ".join(lines.move_id.mapped("display_name")),
                    obligations=", ".join(
                        lines.perf_obligation_id.mapped("display_name")
                    ),
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.perf_obligation_id._mark_needs_recognition()
        return lines

    def write(self, vals):
        before = self.perf_obligation_id
        res = super().write(vals)
        after = self.perf_obligation_id
        (before | after)._mark_needs_recognition()
        return res

    def unlink(self):
        obligations = self.perf_obligation_id
        res = super().unlink()
        obligations._mark_needs_recognition()
        return res
