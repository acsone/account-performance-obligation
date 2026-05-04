# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models

from odoo.addons.queue_job.job import identity_exact


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    def _mark_for_regeneration(self):
        """Mark for regeneration and enqueue an async job to process
        the regeneration.

        The identity key on the obligation id ensures that if a
        regeneration job is already pending for the same obligation,
        no duplicate is enqueued.
        """
        super()._mark_for_regeneration()
        if self.env.context.get("perf_obligation_in_regeneration"):
            return
        for po in self.filtered(
            lambda r: r.schedule_needs_regeneration and r._supports_schedule()
        ):
            po.with_delay(
                identity_key=identity_exact,
                description=f"Regenerate schedule for {po.display_name}",
            )._process_pending_regenerations()
