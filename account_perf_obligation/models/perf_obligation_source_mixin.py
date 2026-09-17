# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, fields, models


class PerfObligationSourceMixin(models.AbstractModel):
    """Mixin for models that act as a source of a performance obligation."""

    _name = "perf.obligation.source.mixin"
    _description = "Performance Obligation Source Mixin"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        copy=False,
        ondelete="restrict",
        index=True,
    )

    def _get_perf_obligation_amount(self):
        """Return the amount this source contributes to its performance
        obligation.
        """
        self.ensure_one()
        raise NotImplementedError(
            _(
                "%(model)s must implement _get_perf_obligation_amount().",
                model=self._name,
            )
        )

    def _get_perf_obligation_partner(self):
        """Return the commercial partner this source sets on its performance
        obligation. Override in source models."""
        self.ensure_one()
        return self.env["res.partner"]

    def _update_perf_obligation_partner(self):
        """Sync the partner of the linked obligations from their sources."""
        for rec in self.filtered("perf_obligation_id"):
            rec.perf_obligation_id.sudo()._update_vals(
                {"partner_id": rec._get_perf_obligation_partner().id},
                _("Partner updated from %(record)s.", record=rec.display_name),
            )

    def _notify_obligation_amount_changed(self):
        """Notify the linked obligation(s) that this source's amount may
        have changed.
        """
        obligations = self.mapped("perf_obligation_id")
        if obligations:
            obligations._update_amount_from_sources()
