# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class PerfObligation(models.Model):
    _inherit = "perf.obligation"

    def _get_obs_config(self, raise_if_missing=True):
        """Return the off-balance sheet configuration for this obligation.

        The commitment account is chosen based on perf_type:
        - income  → po_obs_income_account_id
        - expense → po_obs_expense_account_id

        :param raise_if_missing: if True (default), raises ValidationError when
            any required field is missing on the company.
            If False, returns None instead.
        Returns a dict with keys: journal, commitment_account, counterpart_account,
        or None if raise_if_missing=False and any field is missing.
        """
        self.ensure_one()
        company = self.company_id
        commitment_field = (
            "po_obs_income_account_id"
            if self.perf_type == "income"
            else "po_obs_expense_account_id"
        )
        field_mapping = {
            "journal": "po_obs_journal_id",
            "commitment_account": commitment_field,
            "counterpart_account": "po_obs_counterpart_account_id",
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

    def _get_obs_initial_move_line_vals(self, config):
        """Return the list of line value dicts for the initial OBS journal entry.

        - Debit  : commitment_account (income or expense account per perf_type)
        - Credit : counterpart_account
        """
        self.ensure_one()
        return [
            {
                "account_id": config["commitment_account"].id,
                "debit": self.total_amount,
                "credit": 0.0,
                "perf_obligation_id": self.id,
                "name": self.name,
            },
            {
                "account_id": config["counterpart_account"].id,
                "debit": 0.0,
                "credit": self.total_amount,
                "perf_obligation_id": self.id,
                "name": self.name,
            },
        ]

    def _get_obs_initial_move_vals(self, config):
        """Return the value dict for the initial OBS journal entry."""
        self.ensure_one()
        return {
            "journal_id": config["journal"].id,
            "date": fields.Date.context_today(self),
            "ref": self.name,
            "line_ids": [
                Command.create(line_vals)
                for line_vals in self._get_obs_initial_move_line_vals(config)
            ],
        }

    def _create_obs_initial_move(self):
        """Create the initial off-balance sheet journal entry for this obligation.

        The entry is posted immediately and contains two lines linked to the
        obligation:
        - Debit  : commitment account (income or expense, per perf_type)
        - Credit : counterpart account
        """
        self.ensure_one()
        config = self._get_obs_config()
        move = self.env["account.move"].create(self._get_obs_initial_move_vals(config))
        move.action_post()
        return move

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record._get_obs_config(raise_if_missing=False) is not None:
                record._create_obs_initial_move()
        return records

    def _get_obs_commitment_account_balance(self):
        """Return the current balance of the commitment account (income or
        expense per perf_type) for move lines linked to this obligation
        (draft + posted).
        """
        self.ensure_one()
        config = self._get_obs_config()
        [(balance,)] = self.env["account.move.line"]._read_group(
            domain=[
                ("perf_obligation_id", "=", self.id),
                ("account_id", "=", config["commitment_account"].id),
                ("parent_state", "in", ("draft", "posted")),
            ],
            groupby=[],
            aggregates=["balance:sum"],
        )
        return balance or 0.0

    def _get_obs_adjustment_move_line_vals(
        self, config, debit_account_id, credit_account_id, abs_diff, description
    ):
        """Return the list of line value dicts for an OBS adjustment entry."""
        self.ensure_one()
        return [
            {
                "account_id": debit_account_id,
                "debit": abs_diff,
                "credit": 0.0,
                "perf_obligation_id": self.id,
                "name": description,
            },
            {
                "account_id": credit_account_id,
                "debit": 0.0,
                "credit": abs_diff,
                "perf_obligation_id": self.id,
                "name": description,
            },
        ]

    def _get_obs_adjustment_move_vals(
        self, config, debit_account_id, credit_account_id, abs_diff, description, date
    ):
        """Return the value dict for an OBS adjustment entry at the given date."""
        self.ensure_one()
        return {
            "journal_id": config["journal"].id,
            "date": date,
            "ref": self.name,
            "line_ids": [
                Command.create(line_vals)
                for line_vals in self._get_obs_adjustment_move_line_vals(
                    config, debit_account_id, credit_account_id, abs_diff, description
                )
            ],
        }

    def _adjust_obs(self, date=None):
        """Create an adjustment journal entry if the off-balance sheet
        commitment account balance (A) no longer equals total_amount minus
        the recognized P&L balance up to *date* (B).

        :param date: reference date for filtering recognized P&L move lines
                     (date <= date) and for dating the adjustment entry.
                     Defaults to context_today.

        A > B  → credit the commitment account / debit the counterpart account
        A < B  → debit the commitment account  / credit the counterpart account

        Returns the created account.move, or None if no adjustment is needed.
        """
        self.ensure_one()
        if date is None:
            date = fields.Date.context_today(self)
        precision = self.company_id.currency_id.rounding
        config = self._get_obs_config()
        a = self._get_obs_commitment_account_balance()
        raw_pl = self._get_income_or_expense_balance(date)
        pl_recognized = -raw_pl if self.perf_type == "income" else raw_pl
        b = self.total_amount - pl_recognized
        diff = a - b
        if float_is_zero(diff, precision_rounding=precision):
            return None
        abs_diff = abs(diff)
        if float_compare(diff, 0, precision_rounding=precision) > 0:
            # A > B: credit commitment account, debit counterpart
            debit_account_id = config["counterpart_account"].id
            credit_account_id = config["commitment_account"].id
            description = _(
                "Off-balance sheet adjustment – decrease commitment %(name)s",
                name=self.name,
            )
        else:
            # A < B: debit commitment account, credit counterpart
            debit_account_id = config["commitment_account"].id
            credit_account_id = config["counterpart_account"].id
            description = _(
                "Off-balance sheet adjustment – increase commitment %(name)s",
                name=self.name,
            )
        move = self.env["account.move"].create(
            self._get_obs_adjustment_move_vals(
                config, debit_account_id, credit_account_id, abs_diff, description, date
            )
        )
        move.action_post()
        return move

    def _adjust_obs_job(self, date=None):
        """Job entry-point: adjust a single obligation and return a summary string.

        Designed to be enqueued via queue_job.  Returns a human-readable
        description of the result so that the job success message is useful.
        """
        self.ensure_one()
        move = self._adjust_obs(date=date)
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

    def _enqueue_obs_adjustments(self, obligation_ids, date):
        """Enqueue one _adjust_obs_job per obligation.

        :param obligation_ids: list of perf.obligation ids to process
        :param date: adjustment date (date object)
        """
        obligations = self.env["perf.obligation"].browse(obligation_ids)
        for obligation in obligations:
            obligation.with_delay(
                description=_("OBS adjustment – %(name)s", name=obligation.name),
            )._adjust_obs_job(date=date)
