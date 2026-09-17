# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command

from .common import PerfObligationCommon


class TestRecognizedAmount(PerfObligationCommon):
    """Test recognized_amount / progress."""

    def test_recognized_amount_income(self):
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        self.assertEqual(po.recognized_amount, 0.0)
        self.assertEqual(po.progress, 0.0)

        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
        )
        po.invalidate_recordset()
        self.assertAlmostEqual(po.recognized_amount, 300.0)
        self.assertAlmostEqual(po.progress, 30.0)

    def test_recognized_amount_expense(self):
        po = self._create_obligation(perf_type="expense", total_amount=1000.0)

        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 400, False),
                (self.expense_account, 400, 0, po),
            ],
        )
        po.invalidate_recordset()
        self.assertAlmostEqual(po.recognized_amount, 400.0)
        self.assertAlmostEqual(po.progress, 40.0)

    def test_recognized_amount_ignores_draft_moves(self):
        """Only posted journal items contribute to recognized_amount."""
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        self.env["account.move"].create(
            {
                "journal_id": self.sale_journal.id,
                "date": "2026-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.receivable_account.id,
                            "debit": 500,
                            "credit": 0,
                            "name": "Draft",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.income_account.id,
                            "debit": 0,
                            "credit": 500,
                            "name": "Draft",
                            "perf_obligation_id": po.id,
                        }
                    ),
                ],
            }
        )
        po.invalidate_recordset()
        self.assertEqual(po.recognized_amount, 0.0)
        self.assertEqual(po.progress, 0.0)

    def test_recognized_amount_sums_multiple_accounts_of_same_type(self):
        """Balances on different income accounts linked to the same
        obligation (e.g. the sale invoice account and the recognition P&L
        account) must be summed together."""
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
        )
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 100, 0, po),
                (self.inc_pl, 0, 100, po),
            ],
        )
        po.invalidate_recordset()
        self.assertAlmostEqual(po.recognized_amount, 400.0)

    def test_progress_not_clamped_when_overrecognized(self):
        """progress can exceed 100 when total_amount is reduced below the
        already-recognized amount (e.g. a contract downsizing)"""
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        po.invalidate_recordset()
        self.assertAlmostEqual(po.progress, 100.0)
        po.total_amount = 500.0
        self.assertAlmostEqual(po.recognized_amount, 1000.0)
        self.assertAlmostEqual(po.progress, 200.0)

    def test_progress_can_be_negative(self):
        """progress can go negative when recognized_amount is temporarily
        negative (e.g. a credit note posted ahead of the related invoice)."""
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 0, 200, False),
                (self.income_account, 200, 0, po),
            ],
        )
        po.invalidate_recordset()
        self.assertAlmostEqual(po.recognized_amount, -200.0)
        self.assertAlmostEqual(po.progress, -20.0)

    def test_progress_auto_refreshes_when_total_amount_changes(self):
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
        )
        po.invalidate_recordset()
        self.assertAlmostEqual(po.progress, 30.0)
        po.total_amount = 600.0
        self.assertAlmostEqual(po.progress, 50.0)

    def test_progress_zero_total_amount(self):
        po = self._create_obligation(perf_type="income", total_amount=0.0)
        self.assertEqual(po.progress, 0.0)

    def test_recognized_amount_batched_for_multiple_obligations(self):
        """Two obligations of different types computed together in one
        recordset get their own correct recognized_amount."""
        po_income = self._create_obligation(perf_type="income", total_amount=1000.0)
        po_expense = self._create_obligation(perf_type="expense", total_amount=1000.0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 200, 0, False),
                (self.income_account, 0, 200, po_income),
            ],
        )
        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 150, False),
                (self.expense_account, 150, 0, po_expense),
            ],
        )
        obligations = po_income | po_expense
        obligations.invalidate_recordset()
        self.assertAlmostEqual(po_income.recognized_amount, 200.0)
        self.assertAlmostEqual(po_expense.recognized_amount, 150.0)
