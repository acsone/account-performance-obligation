# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools.misc import format_amount


class ContractLine(models.Model):
    _inherit = "contract.line"

    # is really a one2one
    perf_obligation_ids = fields.One2many(
        comodel_name="perf.obligation",
        inverse_name="contract_line_id",
        string="Performance Obligations",
    )

    def write(self, vals):
        res = super().write(vals)
        if vals.get("is_canceled"):
            self._cancel_perf_obligations()
        return res

    def unlink(self):
        for line in self:
            for obligation in line.perf_obligation_ids:
                draft_move_lines = self.env["account.move.line"].search(
                    [
                        ("perf_obligation_id", "=", obligation.id),
                        ("move_id.state", "=", "draft"),
                    ]
                )
                draft_move_lines.mapped("move_id").unlink()
                obligation.unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.perf_obligation_ids:
                line._update_perf_obligation(line.perf_obligation_ids[0])
            else:
                line._create_perf_obligation_if_needed()
        return lines

    def _create_perf_obligation_if_needed(self):
        """Create a performance obligation for this contract line if applicable.

        Only applies when:
        - the product has auto-create enabled
        - the recognition method is 'contract'
        Duplicate guard: updates existing obligation instead of creating a new one.
        """
        self.ensure_one()
        product = self.product_id
        if not product.perf_obligation_auto_create:
            return None
        if product.perf_obligation_recognition_method != "contract":
            return None
        if self.perf_obligation_ids:
            self._update_perf_obligation(self.perf_obligation_ids[0])
            return self.perf_obligation_ids[0]
        vals = self._prepare_perf_obligation_vals()
        return self.env["perf.obligation"].create(vals)

    def _update_perf_obligation(self, obligation):
        """Resync an existing obligation with current contract line data."""
        self.ensure_one()
        vals = self._prepare_perf_obligation_vals()
        obligation.write(vals)
        obligation._message_log(
            body=_(
                "Values updated from contract line (contract %(contract)s).",
                contract=self.contract_id.name,
            )
        )

    def _prepare_perf_obligation_vals(self):
        """Return the values dict for the performance obligation."""
        self.ensure_one()
        return {
            "perf_type": "income",
            "total_amount": self._get_perf_obligation_total_amount(),
            "start_date": self.date_start,
            "end_date": self.date_end,
            "contract_line_id": self.id,
            "recognition_at_date_method": "daily",
            "description": _(
                "Auto-created from contract %(contract)s - %(product)s",
                contract=self.contract_id.name,
                product=self.product_id.display_name,
            ),
        }

    def _get_perf_obligation_total_amount(self):
        """Compute the total amount for the performance obligation.

        Uses _get_quantity_to_invoice over the full contract line period
        (date_start → date_end) multiplied by the unit price.
        """
        self.ensure_one()
        if not self.date_start or not self.date_end:
            return 0.0
        quantity = self._get_quantity_to_invoice(
            self.date_start,
            self.date_end,
            self.date_start,
        )
        return quantity * self.price_unit

    def _cancel_perf_obligations(self):
        """Update performance obligations on contract line cancellation."""
        for line in self:
            for obligation in line.perf_obligation_ids:
                invoiced_amount = line._get_perf_obligation_invoiced_amount()
                obligation.write({"total_amount": invoiced_amount})
                obligation._message_log(
                    body=_(
                        "Total amount updated to already invoiced amount %(amount)s "
                        "on cancellation of contract line (contract %(contract)s).",
                        amount=format_amount(
                            self.env,
                            invoiced_amount,
                            obligation.currency_id or self.env.company.currency_id,
                        ),
                        contract=line.contract_id.name,
                    )
                )

    def _get_perf_obligation_invoiced_amount(self):
        """Return the sum of amounts already invoiced (posted) for this contract
        line."""
        self.ensure_one()
        move_lines = self.env["account.move.line"].search(
            [
                ("contract_line_id", "=", self.id),
                ("move_id.state", "=", "posted"),
                ("move_id.move_type", "in", ("out_invoice", "out_refund")),
            ]
        )
        invoiced = sum(
            ml.price_subtotal
            if ml.move_id.move_type == "out_invoice"
            else -ml.price_subtotal
            for ml in move_lines
        )
        return max(invoiced, 0.0)

    def _prepare_invoice_line(self):
        vals = super()._prepare_invoice_line()
        if self.perf_obligation_ids:
            vals["perf_obligation_id"] = self.perf_obligation_ids[0].id
        return vals
