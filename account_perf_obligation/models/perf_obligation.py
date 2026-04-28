# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from dataclasses import dataclass

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


@dataclass
class RecognitionConfig:
    journal: object
    pl_account: object
    debit_bs_account: object
    credit_bs_account: object


class PerfObligation(models.Model):
    _name = "perf.obligation"
    _description = "Performance Obligation"

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    perf_type = fields.Selection(
        selection=[
            ("income", "Income"),
            ("expense", "Expense"),
        ],
        string="Type",
        required=True,
    )
    name = fields.Char(
        copy=False,
        default="/",
        readonly=True,
        string="Reference",
    )
    total_amount = fields.Monetary(
        string="Total Amount to Recognize",
        required=True,
    )
    recognition_at_date_method = fields.Selection(
        selection=[],
        help="Method used to compute the amount to recognize at a given date. "
        "Leave empty for manual recognition only.",
    )
    move_line_ids = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="perf_obligation_id",
        string="Journal Items",
        readonly=True,
    )
    move_line_count = fields.Integer(
        compute="_compute_move_line_count",
        string="Journal Items Count",
        readonly=True,
    )
    description = fields.Text()
    supports_schedule = fields.Boolean(
        compute="_compute_supports_schedule",
    )

    @api.depends("recognition_at_date_method")
    def _compute_supports_schedule(self):
        for rec in self:
            rec.supports_schedule = rec._supports_schedule()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "name" not in vals or vals["name"] == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("perf.obligation")
        return super().create(vals_list)

    def _compute_move_line_count(self):
        if not self.ids:
            for rec in self:
                rec.move_line_count = 0
            return
        count_per_obligation = self.env["account.move.line"]._read_group(
            domain=[
                ("perf_obligation_id", "in", self.ids),
                ("parent_state", "in", ("draft", "posted")),
            ],
            groupby=["perf_obligation_id"],
            aggregates=["__count"],
        )
        mapped = {po.id: count for po, count in count_per_obligation}
        for rec in self:
            rec.move_line_count = mapped.get(rec.id, 0)

    def action_view_move_lines(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal Items"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": [
                ("perf_obligation_id", "=", self.id),
                ("parent_state", "in", ("draft", "posted")),
            ],
            "context": {"create": False},
        }

    def _get_recognition_config(self) -> RecognitionConfig:
        """Return recognition configuration for this obligation."""
        self.ensure_one()
        company = self.company_id
        prefix = "po_income" if self.perf_type == "income" else "po_expense"
        field_mapping = {
            "journal": "journal_id",
            "pl_account": "pl_account_id",
            "debit_bs_account": "debit_bs_account_id",
            "credit_bs_account": "credit_bs_account_id",
        }
        values = {}
        missing = []
        for attr, suffix in field_mapping.items():
            field_name = f"{prefix}_{suffix}"
            value = getattr(company, field_name)
            values[attr] = value
            if not value:
                field = self.env["res.company"]._fields[field_name]
                missing.append(field.string)
        if missing:
            raise ValidationError(
                _(
                    "Missing performance obligation configuration "
                    "on company '%(company)s' for %(perf_type)s: "
                    "%(fields)s",
                    company=company.name,
                    perf_type=self.perf_type,
                    fields=", ".join(missing),
                )
            )
        return RecognitionConfig(**values)

    # ------------------------------------------------------------------
    # Recognition at date
    # ------------------------------------------------------------------

    def _supports_recognition_at_date(self):
        """Return whether this obligation supports automatic recognition
        at date computation.

        Override this method to add support for other recognition methods.
        """
        self.ensure_one()
        return bool(self.recognition_at_date_method)

    def _compute_amount_to_recognize_at_date(self, date):
        """Compute the cumulative amount to recognize at the given date.

        Dispatches to the method matching ``recognition_at_date_method``.
        Raises if no recognition method is configured.
        """
        self.ensure_one()
        if not self._supports_recognition_at_date():
            raise ValidationError(
                _(
                    "No recognition at date method configured "
                    "on performance obligation %(name)s.",
                    name=self.display_name,
                )
            )
        method_name = f"_compute_amount_to_recognize_{self.recognition_at_date_method}"
        compute_method = getattr(self, method_name, None)
        if compute_method is None:
            raise ValidationError(
                _(
                    "Unknown recognition method '%(method)s' "
                    "on performance obligation %(name)s.",
                    method=self.recognition_at_date_method,
                    name=self.display_name,
                )
            )
        return compute_method(date)

    # ------------------------------------------------------------------
    # Balance helpers
    # ------------------------------------------------------------------

    def _get_pl_internal_group(self):
        """Return the internal_group value for P&L accounts."""
        self.ensure_one()
        return self.perf_type  # "income" or "expense"

    def _get_income_or_expense_balance(self, date):
        """Get the balance of ALL P&L account lines linked to this
        obligation up to the given date.

        For income: sum of balances on income accounts (I).
        For expense: sum of balances on expense accounts (E).
        """
        self.ensure_one()
        [(balance,)] = self.env["account.move.line"]._read_group(
            domain=[
                ("perf_obligation_id", "=", self.id),
                ("parent_state", "in", ("draft", "posted")),
                ("date", "<=", date),
                (
                    "account_id.internal_group",
                    "=",
                    self._get_pl_internal_group(),
                ),
            ],
            groupby=[],
            aggregates=["balance:sum"],
        )
        return balance or 0.0

    def _get_bs_balances_by_account(self, date):
        """Return a dict {account_id: balance} for all balance sheet
        account lines linked to this obligation up to the given date.
        """
        self.ensure_one()
        balance_per_account = self.env["account.move.line"]._read_group(
            domain=[
                ("perf_obligation_id", "=", self.id),
                ("parent_state", "in", ("draft", "posted")),
                ("date", "<=", date),
                (
                    "account_id.account_type",
                    "in",
                    ("asset_current", "liability_current"),
                ),
            ],
            groupby=["account_id"],
            aggregates=["balance:sum"],
        )
        return {account.id: balance for account, balance in balance_per_account}

    # ------------------------------------------------------------------
    # Recognition logic
    # ------------------------------------------------------------------

    def _recognize(self, amount_to_recognize, date, description):
        """Compute and create a draft recognition journal entry at date
        for the desired amount.

        Returns the created account.move, or None if no adjustment is needed.
        """
        self.ensure_one()
        precision = self.company_id.currency_id.rounding

        if float_compare(amount_to_recognize, 0, precision_rounding=precision) < 0:
            raise ValidationError(_("The amount to recognize cannot be negative."))
        if (
            float_compare(
                amount_to_recognize,
                self.total_amount,
                precision_rounding=precision,
            )
            > 0
        ):
            raise ValidationError(
                _(
                    "The amount to recognize (%(amount)s) cannot exceed "
                    "the total amount on the performance obligation "
                    "(%(total)s).",
                    amount=amount_to_recognize,
                    total=self.total_amount,
                )
            )

        config = self._get_recognition_config()

        lines = self._build_recognition_lines(
            amount_to_recognize, date, config, precision
        )

        if not lines:
            return None

        for line in lines:
            line["name"] = description

        move_vals = {
            "journal_id": config.journal.id,
            "date": date,
            "ref": f"{self.name} - {description}" if description else self.name,
            "auto_post": "at_date",
            "line_ids": [Command.create(vals) for vals in lines],
        }
        return self.env["account.move"].create(move_vals)

    def _build_recognition_lines(self, amount_to_recognize, date, config, precision):
        """Return the list of line value-dicts for the recognition entry.

        Income:
          I = Income Balance (P&L accounts, linked to this obligation)
          R = amount_to_recognize (desired cumulative recognized income)
          DI = -R (desired income balance)
          X = DI - I = Balance Variation

        Expense:
          E = Expense Balance (P&L accounts, linked to this obligation)
          R = amount_to_recognize (desired cumulative recognized expense)
          DE = R (desired expense balance)
          X = DE - E

        Then:
          X < 0: add |X| debit to BS, credit |X| to PL
          X > 0: add |X| credit to BS, debit |X| to PL

        BS adjustments unwind existing opposite balances first,
        grouped by account.
        """
        is_income = self.perf_type == "income"

        # Step 1: Current P&L balance
        pl_balance = self._get_income_or_expense_balance(date)

        # Step 2: balance variation
        if is_income:
            balance_variation = -amount_to_recognize - pl_balance
        else:
            balance_variation = amount_to_recognize - pl_balance

        if float_is_zero(balance_variation, precision_rounding=precision):
            return []

        # Step 3: BS balances by account
        bs_balances = self._get_bs_balances_by_account(date)

        # Step 4: Build lines
        return self._build_lines(balance_variation, config, bs_balances, precision)

    def _build_lines(self, balance_variation, config, bs_balances, precision):
        """Build recognition lines.

        X < 0:
          - Debit each BS account with negative balance to bring it to 0,
            up to |X|.
          - Remaining: debit the configured debit_bs_account.
          - Credit PL for |X|.

        X > 0:
          - Credit each BS account with positive balance to bring it to 0,
            up to |X|.
          - Remaining: credit the configured credit_bs_account.
          - Debit PL for |X|.
        """
        lines = []
        abs_balance_variation = abs(balance_variation)

        if float_compare(balance_variation, 0, precision_rounding=precision) < 0:
            # X < 0: debit BS, credit PL
            remaining = abs_balance_variation

            for account_id, balance in bs_balances.items():
                if float_compare(balance, 0, precision_rounding=precision) < 0:
                    unwind = min(remaining, abs(balance))
                    if not float_is_zero(unwind, precision_rounding=precision):
                        lines.append(
                            self._make_line(account_id, debit=unwind, credit=0)
                        )
                        remaining -= unwind
                    if float_is_zero(remaining, precision_rounding=precision):
                        break

            if not float_is_zero(remaining, precision_rounding=precision):
                lines.append(
                    self._make_line(
                        config.debit_bs_account.id, debit=remaining, credit=0
                    )
                )

            lines.append(
                self._make_line(
                    config.pl_account.id,
                    debit=0,
                    credit=abs_balance_variation,
                )
            )

        elif float_compare(balance_variation, 0, precision_rounding=precision) > 0:
            # X > 0: credit BS, debit PL
            remaining = abs_balance_variation

            for account_id, balance in bs_balances.items():
                if float_compare(balance, 0, precision_rounding=precision) > 0:
                    unwind = min(remaining, balance)
                    if not float_is_zero(unwind, precision_rounding=precision):
                        lines.append(
                            self._make_line(account_id, debit=0, credit=unwind)
                        )
                        remaining -= unwind
                    if float_is_zero(remaining, precision_rounding=precision):
                        break

            if not float_is_zero(remaining, precision_rounding=precision):
                lines.append(
                    self._make_line(
                        config.credit_bs_account.id,
                        debit=0,
                        credit=remaining,
                    )
                )

            lines.append(
                self._make_line(
                    config.pl_account.id,
                    debit=abs_balance_variation,
                    credit=0,
                )
            )

        else:
            return []

        return lines

    def _make_line(self, account_id, debit, credit):
        """Return a journal item value-dict."""
        return {
            "account_id": account_id,
            "debit": debit,
            "credit": credit,
            "perf_obligation_id": self.id,
        }

    # ------------------------------------------------------------------
    # Schedule generation
    # ------------------------------------------------------------------

    def _get_schedule_dates(self):
        """Return the list of dates for which recognition schedule entries
        should be generated.

        Override this method to provide actual dates.
        Must return a list of date objects, sorted ascending.
        """
        self.ensure_one()
        raise NotImplementedError

    def _supports_schedule(self):
        """Return whether this obligation supports schedule generation.

        Override in modules that provide date ranges.
        """
        self.ensure_one()
        return False

    def action_generate_schedule(self):
        """Delete existing draft recognition moves and regenerate
        schedule entries."""
        for po in self:
            if not po._supports_schedule():
                raise ValidationError(
                    _(
                        "Schedule generation is not supported "
                        "on performance obligation %(name)s.",
                        name=po.display_name,
                    )
                )
            po._delete_draft_recognition_moves()
            po._generate_schedule_moves()

    def _get_last_posted_recognition_date(self):
        """Return the date of the last posted recognition move for this
        obligation, or None if there are no posted recognition moves."""
        self.ensure_one()
        config = self._get_recognition_config()
        moves = self.env["account.move"].search(
            [
                ("journal_id", "=", config.journal.id),
                ("state", "=", "posted"),
                ("line_ids.perf_obligation_id", "=", self.id),
            ],
            order="date desc",
            limit=1,
        )
        return moves.date if moves else None

    def _get_draft_recognition_moves(self):
        """Return draft recognition moves for this obligation."""
        self.ensure_one()
        config = self._get_recognition_config()
        return self.env["account.move"].search(
            [
                ("journal_id", "=", config.journal.id),
                ("state", "=", "draft"),
                ("line_ids.perf_obligation_id", "=", self.id),
            ]
        )

    def _delete_draft_recognition_moves(self):
        """Delete all draft recognition journal entries linked to this
        obligation."""
        self.ensure_one()
        draft_moves = self._get_draft_recognition_moves()
        if draft_moves:
            draft_moves.unlink()

    def _generate_schedule_moves(self):
        """Generate draft recognition entries for each schedule date."""
        self.ensure_one()
        dates = self._get_schedule_dates()
        perf_type_label = dict(self._fields["perf_type"].selection).get(
            self.perf_type, self.perf_type
        )

        for schedule_date in dates:
            amount = self._compute_amount_to_recognize_at_date(schedule_date)
            description = _(
                "%(type)s recognition %(date)s",
                type=perf_type_label,
                date=schedule_date,
            )
            self._recognize(
                amount_to_recognize=amount,
                date=schedule_date,
                description=description,
            )
