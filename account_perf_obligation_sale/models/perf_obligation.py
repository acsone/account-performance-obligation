# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sale Order Line",
        index=True,
        copy=False,
        ondelete="restrict",
        help="Sale order line from which this performance obligation "
        "was automatically created.",
    )
