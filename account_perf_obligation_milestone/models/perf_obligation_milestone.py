# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class PerfObligationMilestone(models.Model):
    _name = "perf.obligation.milestone"
    _description = "Performance Obligation Milestone"
    _order = "date, id"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="perf_obligation_id.currency_id",
    )
    name = fields.Char(string="Description")
    date = fields.Date(required=True)
    amount = fields.Monetary(
        string="Cumulative Amount",
        required=True,
        help="Cumulative amount that must be recognized at the end of this "
        "date (not the amount of the step).",
    )
    is_out_of_period = fields.Boolean(
        compute="_compute_is_out_of_period",
        help="The milestone date is outside the recognition period of the "
        "performance obligation: the milestone is ignored.",
    )

    @api.depends(
        "date",
        "perf_obligation_id.start_date",
        "perf_obligation_id.end_date",
    )
    def _compute_is_out_of_period(self):
        for rec in self:
            obligation = rec.perf_obligation_id
            rec.is_out_of_period = bool(
                rec.date
                and obligation.start_date
                and obligation.end_date
                and not obligation.start_date <= rec.date <= obligation.end_date
            )

    @api.constrains("date", "amount", "perf_obligation_id")
    def _check_amounts(self):
        self.perf_obligation_id._check_milestones()

    def _check_obligation_writable(self):
        # A done obligation is locked, milestones included.
        self.perf_obligation_id._check_write_allowed({"milestone_ids": True})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._check_obligation_writable()
        records.perf_obligation_id._mark_needs_recognition()
        return records

    def write(self, vals):
        self._check_obligation_writable()
        before = self.perf_obligation_id
        res = super().write(vals)
        (before | self.perf_obligation_id)._mark_needs_recognition()
        return res

    def unlink(self):
        self._check_obligation_writable()
        obligations = self.perf_obligation_id
        res = super().unlink()
        obligations._mark_needs_recognition()
        return res
