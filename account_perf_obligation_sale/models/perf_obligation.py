# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    sale_order_line_ids = fields.One2many(
        comodel_name="sale.order.line",
        inverse_name="perf_obligation_id",
        string="Sale Order Lines",
        readonly=True,
    )
    sale_order_line_count = fields.Integer(
        compute="_compute_sale_order_line_count",
        string="# Sale Order Lines",
    )

    @api.depends("sale_order_line_ids")
    def _compute_sale_order_line_count(self):
        for rec in self:
            rec.sale_order_line_count = len(rec.sale_order_line_ids)

    def action_view_sale_order_lines(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Sale Order Lines"),
            "res_model": "sale.order.line",
            "view_mode": "list,form",
            "domain": [("perf_obligation_id", "=", self.id)],
            "context": {"create": False},
        }
        if len(self.sale_order_line_ids) == 1:
            action.update({"view_mode": "form", "res_id": self.sale_order_line_ids.id})
        return action
