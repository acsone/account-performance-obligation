# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.tests.common import TransactionCase


class PerfObligationObsCommitmentCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, queue_job__no_delay=True))
        cls.company = cls.env.ref("base.main_company")
        cls.currency = cls.company.currency_id
        cls.today = fields.Date.today()

        Account = cls.env["account.account"]

        # ── Standard P&L / BS accounts ───────────────────────────────────

        cls.income_account = Account.create(
            {"name": "Income", "code": "707OBS", "account_type": "income"}
        )
        cls.expense_account = Account.create(
            {"name": "Expense", "code": "607OBS", "account_type": "expense"}
        )
        cls.receivable_account = Account.create(
            {
                "name": "Receivable",
                "code": "411OBS",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.payable_account = Account.create(
            {
                "name": "Payable",
                "code": "401OBS",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )

        # ── Income recognition accounts ───────────────────────────────────

        cls.inc_pl = Account.create(
            {"name": "Income Reco P&L", "code": "7R1OBS", "account_type": "income"}
        )
        cls.inc_debit_bs = Account.create(
            {
                "name": "Income Accrual BS",
                "code": "418OBS",
                "account_type": "asset_current",
            }
        )
        cls.inc_credit_bs = Account.create(
            {
                "name": "Income Deferral BS",
                "code": "487OBS",
                "account_type": "liability_current",
            }
        )

        # ── Expense recognition accounts ──────────────────────────────────

        cls.exp_pl = Account.create(
            {"name": "Expense Reco P&L", "code": "6R1OBS", "account_type": "expense"}
        )
        cls.exp_debit_bs = Account.create(
            {
                "name": "Expense Deferral BS",
                "code": "486OBS",
                "account_type": "asset_current",
            }
        )
        cls.exp_credit_bs = Account.create(
            {
                "name": "Expense Accrual BS",
                "code": "408OBS",
                "account_type": "liability_current",
            }
        )

        # ── Off-balance sheet accounts ────────────────────────────────────

        cls.obs_income_account = Account.create(
            {
                "name": "OBS Commitment Income",
                "code": "8IOBST",
                "account_type": "off_balance",
            }
        )
        cls.obs_expense_account = Account.create(
            {
                "name": "OBS Commitment Expense",
                "code": "8EOBST",
                "account_type": "off_balance",
            }
        )
        cls.obs_counter_account = Account.create(
            {
                "name": "OBS Commitment Counterpart",
                "code": "9COBST",
                "account_type": "off_balance",
            }
        )

        # ── Journals ──────────────────────────────────────────────────────

        cls.reco_journal = cls.env["account.journal"].create(
            {
                "name": "Income Recognition OBS",
                "code": "ROBS",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.exp_reco_journal = cls.env["account.journal"].create(
            {
                "name": "Expense Recognition OBS",
                "code": "EOBS",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.obs_journal = cls.env["account.journal"].create(
            {
                "name": "Off-Balance Sheet OBS",
                "code": "OOBS",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": "Sales OBS",
                "code": "SOBS",
                "type": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Purchase OBS",
                "code": "POBS",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )

        # ── Company configuration ─────────────────────────────────────────

        cls.company.write(
            {
                # income recognition
                "po_income_journal_id": cls.reco_journal.id,
                "po_income_pl_account_id": cls.inc_pl.id,
                "po_income_debit_bs_account_id": cls.inc_debit_bs.id,
                "po_income_credit_bs_account_id": cls.inc_credit_bs.id,
                # expense recognition
                "po_expense_journal_id": cls.exp_reco_journal.id,
                "po_expense_pl_account_id": cls.exp_pl.id,
                "po_expense_debit_bs_account_id": cls.exp_debit_bs.id,
                "po_expense_credit_bs_account_id": cls.exp_credit_bs.id,
                # off-balance sheet
                "po_obs_commitment_journal_id": cls.obs_journal.id,
                "po_obs_commitment_income_account_id": cls.obs_income_account.id,
                "po_obs_commitment_expense_account_id": cls.obs_expense_account.id,
                "po_obs_commitment_counterpart_account_id": cls.obs_counter_account.id,
            }
        )

        # ── Partner ───────────────────────────────────────────────────────

        cls.partner = cls.env["res.partner"].create(
            {
                "name": "OBS Commitment Test Partner",
                "property_account_receivable_id": cls.receivable_account.id,
                "property_account_payable_id": cls.payable_account.id,
            }
        )

    def _create_obligation(self, perf_type="income", total_amount=1000.0):
        return self.env["perf.obligation"].create(
            {
                "perf_type": perf_type,
                "total_amount": total_amount,
                "company_id": self.company.id,
            }
        )

    def _create_and_post_move(self, journal, line_specs, date="2026-01-01"):
        move = self.env["account.move"].create(
            {
                "journal_id": journal.id,
                "date": date,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": account.id,
                            "debit": debit,
                            "credit": credit,
                            "name": "Test",
                            "perf_obligation_id": (po.id if po else False),
                        }
                    )
                    for account, debit, credit, po in line_specs
                ],
            }
        )
        move.action_post()
        return move

    def _get_obs_lines(self, po):
        """Return all move lines in the OBS commitment journal linked to *po*."""
        return self.env["account.move.line"].search(
            [
                ("perf_obligation_id", "=", po.id),
                ("move_id.journal_id", "=", self.obs_journal.id),
                ("parent_state", "in", ("draft", "posted")),
            ]
        )

    def _obs_commitment_balance(self, po):
        """Return the balance of the OBS commitment account for *po*
        (income or expense account depending on perf_type)."""
        return po._get_obs_commitment_account_balance()
