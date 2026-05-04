# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models

from odoo.addons.queue_job.job import identity_exact


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    def _mark_for_regeneration(self):
        marked = super()._mark_for_regeneration()
        for po in marked:
            po.with_delay(
                identity_key=identity_exact,
                description=f"Regenerate schedule for {po.display_name}",
            )._process_pending_regenerations()
        return marked
