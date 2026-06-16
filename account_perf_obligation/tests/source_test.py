# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class PerfObligationTestSource(models.TransientModel):
    _name = "perf.obligation.test.source"
    _description = "Test Source for Performance Obligation Mixin"
    _inherit = ["perf.obligation.source.mixin"]

    amount = fields.Float()

    def _get_perf_obligation_amount(self):
        self.ensure_one()
        return self.amount
