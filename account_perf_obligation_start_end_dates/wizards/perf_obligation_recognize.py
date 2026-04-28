# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class PerfObligationRecognize(models.TransientModel):
    _inherit = "perf.obligation.recognize"

    amount_to_recognize = fields.Monetary(
        compute="_compute_amount_to_recognize",
        store=True,
        readonly=False,
        required=False,
    )

    @api.depends("perf_obligation_id", "date")
    def _compute_amount_to_recognize(self):
        for wizard in self:
            obligation = wizard.perf_obligation_id
            if (
                obligation
                and wizard.date
                and obligation._supports_recognition_at_date()
            ):
                wizard.amount_to_recognize = (
                    obligation._compute_amount_to_recognize_at_date(wizard.date)
                )
