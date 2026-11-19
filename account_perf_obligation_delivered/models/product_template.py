# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    perf_obligation_at_date_method = fields.Selection(
        selection_add=[
            ("delivered", "Delivered Amount + Projected Balance"),
        ],
    )
