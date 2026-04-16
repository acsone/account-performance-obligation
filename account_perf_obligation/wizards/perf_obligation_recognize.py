# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class PerfObligationRecognize(models.TransientModel):
    _name = "perf.obligation.recognize"
    _description = "Recognize Income/Expense on Performance Obligation"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        required=True,
        readonly=True,
    )
    perf_type = fields.Selection(
        related="perf_obligation_id.perf_type",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="perf_obligation_id.company_id.currency_id",
    )
    total_amount = fields.Float(
        related="perf_obligation_id.total_amount",
        string="Total Amount to Recognize",
    )
    date = fields.Date(
        string="Recognition Date",
        required=True,
        default=fields.Date.context_today,
    )
    amount_to_recognize = fields.Float(
        string="Amount to Recognize at Date",
        required=True,
        help="The cumulative amount that should be recognized as of the "
        "given date. Must not exceed the total amount on the obligation.",
    )
    description = fields.Char(
        required=True,
    )

    def action_confirm(self):
        self.ensure_one()
        move = self.perf_obligation_id._recognize(
            amount_to_recognize=self.amount_to_recognize,
            date=self.date,
            description=self.description,
        )
        if not move:
            raise UserError(
                _(
                    "No adjustment is needed: the recognized amount "
                    "already matches the desired amount."
                )
            )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }
