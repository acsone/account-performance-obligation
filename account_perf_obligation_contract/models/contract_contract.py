# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    perf_obligation_count = fields.Integer(
        compute="_compute_perf_obligation_count",
        string="Performance Obligations",
        readonly=True,
    )

    @api.depends("contract_line_ids.perf_obligation_id")
    def _compute_perf_obligation_count(self):
        for contract in self:
            contract.perf_obligation_count = len(
                contract.contract_line_ids.mapped("perf_obligation_id")
            )

    def action_view_perf_obligations(self):
        self.ensure_one()
        obligation_ids = self.contract_line_ids.mapped("perf_obligation_id").ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Performance Obligations"),
            "res_model": "perf.obligation",
            "view_mode": "list,form",
            "domain": [("id", "in", obligation_ids)],
            "context": {"create": False},
        }
