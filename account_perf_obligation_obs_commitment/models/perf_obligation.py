# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import Command, _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero

_logger = logging.getLogger(__name__)


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    def _get_obs_commitment_config(self, raise_if_missing=True):
        """Return the off-balance sheet configuration for this obligation.

        The commitment account is chosen based on perf_type:
        - income  → po_obs_commitment_income_account_id
        - expense → po_obs_commitment_expense_account_id

        :param raise_if_missing: if True (default), raises ValidationError when
            any required field is missing on the company.
            If False, returns None instead.
        Returns a dict with keys: journal, commitment_account, counterpart_account,
        or None if raise_if_missing=False and any field is missing.
        """
        self.ensure_one()
        company = self.company_id
        commitment_field = (
            "po_obs_commitment_income_account_id"
            if self.perf_type == "income"
            else "po_obs_commitment_expense_account_id"
        )
        field_mapping = {
            "journal": "po_obs_commitment_journal_id",
            "commitment_account": commitment_field,
            "counterpart_account": "po_obs_commitment_counterpart_account_id",
        }
        values = {}
        missing = []
        for attr, field_name in field_mapping.items():
            value = getattr(company, field_name)
            values[attr] = value
            if not value:
                field = self.env["res.company"]._fields[field_name]
                missing.append(field.string)
        if missing:
            if not raise_if_missing:
                return None
            raise ValidationError(
                _(
                    "Missing off-balance sheet configuration "
                    "on company '%(company)s': %(fields)s",
                    company=company.name,
                    fields=", ".join(missing),
                )
            )
        return values

    def _get_obs_commitment_account_balance(self, date=None):
        """Return the current balance of the commitment account.

        :param date: if provided, only lines with date <= date are included.
        """
        self.ensure_one()
        config = self._get_obs_commitment_config()
        domain = [
            ("perf_obligation_id", "=", self.id),
            ("account_id", "=", config["commitment_account"].id),
            ("parent_state", "=", "posted"),
        ]
        if date:
            domain.append(("date", "<=", date))
        [(balance,)] = self.env["account.move.line"]._read_group(
            domain=domain,
            groupby=[],
            aggregates=["balance:sum"],
        )
        return balance or 0.0

    def _get_obs_adjustment_move_line_vals(self, config, balance_adjustment):
        """Return line vals for an OBS adjustment entry."""
        self.ensure_one()
        abs_adj = abs(balance_adjustment)
        if balance_adjustment > 0:
            commitment_debit, commitment_credit = abs_adj, 0.0
            counterpart_debit, counterpart_credit = 0.0, abs_adj
            description = _("OBS – increase commitment %(name)s", name=self.name)
        else:
            commitment_debit, commitment_credit = 0.0, abs_adj
            counterpart_debit, counterpart_credit = abs_adj, 0.0
            description = _("OBS – decrease commitment %(name)s", name=self.name)
        return [
            {
                "account_id": config["commitment_account"].id,
                "debit": commitment_debit,
                "credit": commitment_credit,
                "perf_obligation_id": self.id,
                "name": description,
            },
            {
                "account_id": config["counterpart_account"].id,
                "debit": counterpart_debit,
                "credit": counterpart_credit,
                "perf_obligation_id": self.id,
                "name": description,
            },
        ]

    def _get_obs_commitment_adjustment_move_vals(
        self, config, date, balance_adjustment
    ):
        """Return the value dict for an OBS commitment adjustment entry at the given
        date."""
        self.ensure_one()
        return {
            "journal_id": config["journal"].id,
            "date": date,
            "ref": self.name,
            "line_ids": [
                Command.create(line_vals)
                for line_vals in self._get_obs_adjustment_move_line_vals(
                    config, balance_adjustment
                )
            ],
        }

    def _get_desired_obs_commitment_balance(self, date):
        """Return the target balance for the commitment account at date.

        = total_amount minus the recognized P&L amount up to date.
        """
        self.ensure_one()
        raw_pl = self._get_income_or_expense_balance(date)
        pl_recognized = -raw_pl if self.perf_type == "income" else raw_pl
        return self.total_amount - pl_recognized

    def _adjust_obs_commitment(self, date=None):
        """Create an adjustment journal entry if necessary"""
        self.ensure_one()
        if date is None:
            date = fields.Date.context_today(self)
        precision = self.company_id.currency_id.rounding
        config = self._get_obs_commitment_config()
        current_balance = self._get_obs_commitment_account_balance(date=date)
        desired_balance = self._get_desired_obs_commitment_balance(date)
        balance_adjustment = desired_balance - current_balance
        if float_is_zero(balance_adjustment, precision_rounding=precision):
            return None
        move = self.env["account.move"].create(
            self._get_obs_commitment_adjustment_move_vals(
                config, date, balance_adjustment
            )
        )
        move.action_post()
        return move

    def _adjust_obs_commitment_job(self, date=None):
        """Job entry-point: adjust a single obligation and return a summary string.

        Designed to be enqueued via queue_job.  Returns a human-readable
        description of the result so that the job success message is useful.
        """
        self.ensure_one()
        move = self._adjust_obs_commitment(date=date)
        if move:
            return _(
                "Off-balance sheet adjustment entry %(move)s created "
                "for obligation %(name)s.",
                move=move.name,
                name=self.name,
            )
        return _(
            "No adjustment needed for obligation %(name)s.",
            name=self.name,
        )

    def _enqueue_obs_commitment_adjustments(self, obligation_ids, date):
        """Enqueue one _adjust_obs_commitment_job per obligation.

        :param obligation_ids: list of perf.obligation ids to process
        :param date: adjustment date (date object)
        """
        obligations = self.env["perf.obligation"].browse(obligation_ids)
        for obligation in obligations:
            obligation.with_delay(
                description=_(
                    "OBS commitment adjustment – %(name)s", name=obligation.name
                ),
            )._adjust_obs_commitment_job(date=date)
