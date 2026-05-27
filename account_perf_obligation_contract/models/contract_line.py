# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_amount


class ContractLine(models.Model):
    _name = "contract.line"
    _inherit = ["contract.line", "perf.obligation.source.mixin"]

    perf_obligation_auto_create = fields.Boolean(
        string="Auto-create Performance Obligation",
    )

    def write(self, vals):
        res = super().write(vals)
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
        sources = obligation._get_sources()
        if sources != [self]:
            raise ValidationError(
                _(
                    "Performance obligation %(obligation)s originates from "
                    "multiple sources %(sources)s, so it can't be updated "
                    "automatically to match the contract line.",
                    sources=", ".join(
                        [r.display_name for recordset in sources for r in recordset]
                    ),
                    obligation=obligation.display_name,
                )
            )
        vals = self._prepare_perf_obligation_vals()
        obligation.sudo().write(vals)
        obligation.sudo()._message_log(
            body=_(
                "Values updated from contract line (contract %(contract)s).",
                contract=self.contract_id.name,
            )
        )

    def _prepare_perf_obligation_vals(self):
        """Return the values dict for the performance obligation."""
        self.ensure_one()
        contract_type = self.contract_id.contract_type
        perf_type = False
        if self.contract_id.contract_type == "sale":
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
            "total_amount": self._get_obligation_amount(),
            "start_date": self.date_start,
            "end_date": self.date_end,
            "recognition_at_date_method": "daily",
            "description": _(
                "Auto-created from contract %(contract)s",
                contract=self.contract_id.name,
            ),
        }
        pl_account = self._get_perf_obligation_pl_account()
        if pl_account:
            vals["pl_account_id"] = pl_account.id
        return vals

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

    def _get_obligation_amount(self):
        return self._get_contract_line_total_value()

    def _cancel_perf_obligations(self):
        """Update performance obligations on contract line cancellation."""
        for line in self:
            obligation = line.perf_obligation_id
            if not obligation:
                continue
            invoiced_amount = line._get_perf_obligation_invoiced_amount()
            obligation.sudo().write({"total_amount": invoiced_amount})
            obligation.sudo()._message_log(
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

    def _get_perf_obligation_invoiced_amount_domain(self, move_types):
        """Return the domain to find invoice lines for this contract line."""
        self.ensure_one()
        domain = [
            ("contract_line_id", "=", self.id),
            ("move_id.state", "=", "posted"),
            ("move_id.move_type", "in", move_types),
        ]
        if self.perf_obligation_id:
            domain.append(("perf_obligation_id", "=", self.perf_obligation_id.id))
        return domain

    def _get_perf_obligation_invoiced_amount(self):
        """Return the sum of amounts already invoiced (posted) for this contract
        line."""
        self.ensure_one()
        contract_type = self.contract_id.contract_type
        if contract_type == "sale":
            move_types = ("out_invoice", "out_refund")
        elif contract_type == "purchase":
            move_types = ("in_invoice", "in_refund")
        domain = self._get_perf_obligation_invoiced_amount_domain(move_types)
        [(balance,)] = self.env["account.move.line"]._read_group(
            domain=domain,
            aggregates=["balance:sum"],
        )
        # AML balance is credit-negative for customer invoices; negate to get a
        # positive invoiced amount for sales, use directly for purchases
        sign = -1 if contract_type == "sale" else 1
        invoiced = sign * (balance or 0.0)
        if invoiced < 0.0:
            raise ValidationError(
                _(
                    "Contract line %(line)s has a negative net invoiced amount "
                    "%(amount)s. This likely means refunds exceed posted invoices.",
                    line=self.display_name,
                    amount=format_amount(
                        self.env,
                        invoiced,
                        self.contract_id.currency_id or self.env.company.currency_id,
                    ),
                )
            )
        return invoiced

    def _prepare_invoice_line(self):
        vals = super()._prepare_invoice_line()
        if self.perf_obligation_id:
            vals["perf_obligation_id"] = self.perf_obligation_id.id
        return vals
