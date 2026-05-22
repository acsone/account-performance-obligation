# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PerfObligationObsCommitmentAdjustWizard(models.TransientModel):
    _name = "perf.obligation.obs.commitment.adjust.wizard"
    _description = "Adjust Off-Balance Sheet Commitments"

    @api.model
    def _default_date(self):
        today = fields.Date.context_today(self)
        return today - relativedelta(months=1, day=31)

    date = fields.Date(
        string="Adjustment Date",
        required=True,
        default=_default_date,
    )

    def action_adjust(self):
        """Enqueue one queue_job per obligation at the chosen date.

        When called from the action menu on a selection of obligations the
        context key ``active_ids`` is used to restrict processing to that
        selection.  When called from the global menu item all obligations are
        processed.
        """
        self.ensure_one()
        active_ids = self.env.context.get("active_ids")
        if active_ids:
            obligations = self.env["perf.obligation"].browse(active_ids)
        else:
            obligations = self.env["perf.obligation"].search([])
        self.env["perf.obligation"]._enqueue_obs_commitment_adjustments(
            obligations.ids, self.date
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Off-Balance Sheet Adjustments"),
                "message": _(
                    "%(count)s job(s) enqueued. "
                    "Check the Queue Jobs menu for their status.",
                    count=len(obligations),
                ),
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
