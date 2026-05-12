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

    @api.depends("contract_line_ids.perf_obligation_ids")
    def _compute_perf_obligation_count(self):
        groups = self.env["perf.obligation"]._read_group(
            domain=[("contract_line_id", "in", self.mapped("contract_line_ids").ids)],
            groupby=["contract_line_id"],
            aggregates=["__count"],
        )
        counts = {line.id: count for line, count in groups}
        for contract in self:
            contract.perf_obligation_count = sum(
                counts.get(line.id, 0) for line in contract.contract_line_ids
            )

    def action_view_perf_obligations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Performance Obligations"),
            "res_model": "perf.obligation",
            "view_mode": "list,form",
            "domain": [("contract_line_id", "in", self.contract_line_ids.ids)],
            "context": {"create": False},
        }
