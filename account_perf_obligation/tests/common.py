# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, fields
from odoo.tests.common import TransactionCase


class PerfObligationCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.currency = cls.company.currency_id
        cls.today = fields.Date.today()

        Account = cls.env["account.account"]

        # Income P&L (normal invoice account)
        cls.income_account = Account.create(
            {
                "name": "Income",
                "code": "707TST",
                "account_type": "income",
            }
        )

        # Expense P&L (normal invoice account)
        cls.expense_account = Account.create(
            {
                "name": "Expense",
                "code": "607TST",
                "account_type": "expense",
            }
        )

        # Receivable / Payable
        cls.receivable_account = Account.create(
            {
                "name": "Receivable",
                "code": "411TST",
                "account_type": "asset_receivable",
                "reconcile": True,
            }
        )
        cls.payable_account = Account.create(
            {
                "name": "Payable",
                "code": "401TST",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )

        # Income recognition accounts
        cls.inc_pl = Account.create(
            {
                "name": "Income Recognition P&L",
                "code": "7R1TST",
                "account_type": "income",
            }
        )
        cls.inc_debit_bs = Account.create(
            {
                "name": "Income Accrual BS",
                "code": "418TST",
                "account_type": "asset_current",
            }
        )
        cls.inc_credit_bs = Account.create(
            {
                "name": "Income Deferral BS",
                "code": "487TST",
                "account_type": "liability_current",
            }
        )

        # Expense recognition accounts
        cls.exp_pl = Account.create(
            {
                "name": "Expense Recognition P&L",
                "code": "6R1TST",
                "account_type": "expense",
            }
        )
        cls.exp_debit_bs = Account.create(
            {
                "name": "Expense Deferral BS",
                "code": "486TST",
                "account_type": "asset_current",
            }
        )
        cls.exp_credit_bs = Account.create(
            {
                "name": "Expense Accrual BS",
                "code": "408TST",
                "account_type": "liability_current",
            }
        )

        # Journals
        cls.reco_journal = cls.env["account.journal"].create(
            {
                "name": "Income Recognition",
                "code": "RECO",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.exp_reco_journal = cls.env["account.journal"].create(
            {
                "name": "Expense Recognition",
                "code": "EREC",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.sale_journal = cls.env["account.journal"].create(
            {
                "name": "Sales Test",
                "code": "SALT",
                "type": "sale",
                "company_id": cls.company.id,
            }
        )
        cls.purchase_journal = cls.env["account.journal"].create(
            {
                "name": "Purchase Test",
                "code": "PURT",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )

        # Configure company
        cls.company.write(
            {
                "po_income_journal_id": cls.reco_journal.id,
                "po_income_pl_account_id": cls.inc_pl.id,
                "po_income_debit_bs_account_id": cls.inc_debit_bs.id,
                "po_income_credit_bs_account_id": cls.inc_credit_bs.id,
                "po_expense_journal_id": cls.exp_reco_journal.id,
                "po_expense_pl_account_id": cls.exp_pl.id,
                "po_expense_debit_bs_account_id": cls.exp_debit_bs.id,
                "po_expense_credit_bs_account_id": cls.exp_credit_bs.id,
            }
        )

        # Partner
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Test Partner",
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

    def _create_and_post_move(self, journal, line_specs, date="2025-01-01"):
        """Create and post a journal entry.

        line_specs: list of (account, debit, credit, obligation_or_False)
        """
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
                        },
                    )
                    for account, debit, credit, po in line_specs
                ],
            }
        )
        move.action_post()
        return move

    def _create_wizard(
        self,
        obligation,
        amount,
        date="2025-01-31",
        description="Reco test",
    ):
        return self.env["perf.obligation.recognize"].create(
            {
                "perf_obligation_id": obligation.id,
                "amount_to_recognize": amount,
                "date": date,
                "description": description,
            }
        )

    def _filter_lines(self, lines, account):
        """Filter move lines by account (ruff E741 safe)."""
        return lines.filtered(lambda line, acc=account: line.account_id == acc)

    def _get_bs_balance(self, po, account, date):
        """Return the BS balance for a specific account on a perf obligation."""
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        bs_balances = po._get_bs_balances_by_account(date)
        return bs_balances.get(account.id, 0.0)
