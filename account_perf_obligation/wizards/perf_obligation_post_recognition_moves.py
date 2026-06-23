# account_perf_obligation/wizards/perf_obligation_post_recognition_moves.py

from odoo import Command, _, api, fields, models


class PerfObligationPostRecognitionMoves(models.TransientModel):
    _name = "perf.obligation.post.recognition.moves"
    _description = "Post Performance Obligation Recognition Moves"

    perf_obligation_ids = fields.Many2many(
        comodel_name="perf.obligation",
        string="Performance Obligations",
        help="Performance obligations to post recognition moves for. "
        "If empty, processes all pending moves.",
    )
    date = fields.Date(
        string="Posting Date",
        required=True,
        default=fields.Date.context_today,
        help="Draft recognition entries dated on or before this date will "
        "be posted.",
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if active_model == "perf.obligation" and active_ids:
            vals["perf_obligation_ids"] = [Command.set(active_ids)]
        return vals

    def action_confirm(self):
        self.ensure_one()
        if self.perf_obligation_ids:
            self.perf_obligation_ids.action_post_recognition_moves(self.date)
        else:
            self.env["perf.obligation"]._post_all_recognition_moves(
                self.date, companies=self.env.companies
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Posting scheduled"),
                "message": _(
                    "Eligible recognition moves have been marked for posting "
                    "and will be posted shortly."
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
