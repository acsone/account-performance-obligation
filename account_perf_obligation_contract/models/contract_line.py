# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_amount


class ContractLine(models.Model):
    _name = "contract.line"
    _inherit = ["contract.line", "perf.obligation.source.mixin"]

    perf_obligation_auto_create = fields.Boolean(
        string="Auto-create Performance Obligation",
    )

    def write(self, vals):
        res = super().write(vals)
        if set(vals) - {"perf_obligation_id"}:
            for line in self:
                line._create_or_update_perf_obligation()
        if vals.get("is_canceled"):
            self._cancel_perf_obligations()
        return res

    def unlink(self):
        for line in self:
            obligation = line.perf_obligation_id
            if obligation:
                line.perf_obligation_id = False
                obligation.sudo().unlink()
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            line._create_or_update_perf_obligation()
        return lines

    def _create_or_update_perf_obligation(self):
        """Create or update a performance obligation for this contract line if
        applicable.

        Only applies when:
        - the perf_obligation_auto_create is checked
        """
        self.ensure_one()
        if not self.perf_obligation_auto_create:
            return None
        if self.perf_obligation_id:
            self._update_perf_obligation(self.perf_obligation_id)
            return self.perf_obligation_id
        vals = self._prepare_perf_obligation_vals()
        obligation = self.env["perf.obligation"].sudo().create(vals)
        self.perf_obligation_id = obligation
        return obligation

    def _update_perf_obligation(self, obligation):
        """Resync an existing obligation with current contract line data."""
        self.ensure_one()
        obligation._ensure_sole_source(self)
        obligation._update_vals(
            self._prepare_perf_obligation_vals(),
            _(
                "Values updated from contract line (contract %(contract)s).",
                contract=self.contract_id.name,
            ),
        )

    def _prepare_perf_obligation_vals(self):
        self.ensure_one()
        contract_type = self.contract_id.contract_type
        perf_type = False
        if contract_type == "sale":
            perf_type = "income"
        elif contract_type == "purchase":
            perf_type = "expense"
        if not perf_type:
            raise ValidationError(
                _(
                    "Unknown contract type '%(contract_type)s' "
                    "on contract '%(contract)s'.",
                    contract_type=contract_type,
                    contract=self.contract_id.display_name,
                )
            )
        vals = {
            "perf_type": perf_type,
            "total_amount": self._get_perf_obligation_amount(),
            "start_date": self.date_start,
            "end_date": self.date_end,
            "description": _(
                "Auto-created from contract %(contract)s",
                contract=self.contract_id.name,
            ),
            "recognition_at_date_method": (
                self._get_obligation_recognition_at_date_method()
            ),
        }
        pl_account = self._get_perf_obligation_pl_account()
        if pl_account:
            vals["pl_account_id"] = pl_account.id
        return vals

    def _get_obligation_recognition_at_date_method(self):
        """Return the recognition method to use on the performance obligation.

        Returns 'daily' when both start and end dates are set.
        Raises UserError for open-ended lines, since a date-based recognition
        method cannot be applied without a known end date.
        """
        self.ensure_one()
        if self.date_start and self.date_end:
            return "daily"
        raise UserError(
            _(
                "Cannot determine a recognition method for contract line '%s': "
                "both a start date and an end date are required to auto-create "
                "a performance obligation.",
                self.display_name,
            )
        )

    def _get_perf_obligation_pl_account(self):
        """Return the P&L account to set on the performance obligation.

        For sale contracts: resolves the product's income account.
        For purchase contracts: resolves the product's expense account.
        """
        self.ensure_one()
        account_key = {"sale": "income", "purchase": "expense"}.get(
            self.contract_id.contract_type
        )
        if not account_key:
            return None
        accounts = self.product_id.with_company(
            self.contract_id.company_id
        ).product_tmpl_id.get_product_accounts(
            fiscal_pos=self.contract_id.fiscal_position_id
        )
        return accounts.get(account_key)

    def _get_perf_obligation_amount(self):
        return self._get_contract_line_total_value()

    def _cancel_perf_obligations(self):
        """Update performance obligations on contract line cancellation."""
        for line in self:
            if line.perf_obligation_id:
                obligation = line.perf_obligation_id
                obligation._ensure_sole_source(line)
                invoiced_amount = obligation._get_invoiced_amount()
                obligation._update_total_amount(
                    invoiced_amount,
                    _(
                        "Total amount updated to already invoiced amount %(amount)s"
                        " on cancellation of %(cancelled_source)s.",
                        amount=format_amount(
                            obligation.env,
                            invoiced_amount,
                            obligation.currency_id
                            or obligation.env.company.currency_id,
                        ),
                        cancelled_source=_("contract line (contract %s)")
                        % line.contract_id.name,
                    ),
                )

    def _prepare_invoice_line(self):
        vals = super()._prepare_invoice_line()
        if self.perf_obligation_id:
            vals["perf_obligation_id"] = self.perf_obligation_id.id
        return vals
