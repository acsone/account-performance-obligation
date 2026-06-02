# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    contract_line_ids = fields.One2many(
        comodel_name="contract.line",
        inverse_name="perf_obligation_id",
        string="Contract Lines",
        readonly=True,
    )
    contract_line_count = fields.Integer(
        compute="_compute_contract_line_count",
        string="# Contract Lines",
    )

    @api.depends("contract_line_ids")
    def _compute_contract_line_count(self):
        for rec in self:
            rec.contract_line_count = len(rec.contract_line_ids)

    def action_view_contract_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Contract Lines"),
            "res_model": "contract.line",
            "view_mode": "list,form",
            "domain": [("perf_obligation_id", "=", self.id)],
            "context": {"create": False},
        }
