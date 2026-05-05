# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from .common import PerfObligationCommon


class TestSchedule(PerfObligationCommon):
    def test_expense_schedule_without_bill_has_zero_billed_amount(self):
        """Recognizing expense before receiving the bill creates an accrual,
        but the billed amount must remain zero.
        """
        po = self._create_obligation(perf_type="expense", total_amount=1000)

        result = self._create_wizard(
            po,
            100,
            date="2026-01-31",
            description="Jan",
        ).action_confirm()

        move = self.env["account.move"].browse(result["res_id"])
        self.assertTrue(move)

        # The schedule is an SQL view based on account.move.line.
        # Flush accounting lines before querying the view.
        self.env["account.move.line"].flush_model()
        self.env["account.move"].flush_model()

        schedule_line = self.env["perf.obligation.schedule.expense"].search(
            [("perf_obligation_id", "=", po.id)],
            limit=1,
        )

        self.assertTrue(schedule_line)

        self.assertAlmostEqual(schedule_line.recognized_amount, 100)
        self.assertAlmostEqual(schedule_line.deferred_accrued_amount, 100)

        # No vendor bill exists yet, so billed must be zero.
        self.assertAlmostEqual(schedule_line.billed_amount, 0)
        self.assertAlmostEqual(schedule_line.total_billed_amount, 0)
        self.assertAlmostEqual(schedule_line.total_recognized_amount, 100)
        self.assertAlmostEqual(schedule_line.total_deferred_accrued_amount, 100)

    def test_get_move_lines_date_range_no_lines(self):
        po = self._create_obligation(total_amount=1000.0)
        min_date, max_date = po._get_move_lines_date_range()
        self.assertFalse(min_date)
        self.assertFalse(max_date)

    def test_get_move_lines_date_range_with_lines(self):
        po = self._create_obligation(total_amount=1000.0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 500, 0, False),
                (self.income_account, 0, 500, po),
            ],
            date="2026-01-15",
        )
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 500, 0, False),
                (self.income_account, 0, 500, po),
            ],
            date="2026-03-20",
        )
        min_date, max_date = po._get_move_lines_date_range()
        self.assertEqual(min_date, date(2026, 1, 15))
        self.assertEqual(max_date, date(2026, 3, 20))

    def test_schedule_income_invoice_and_reco_are_segregated(self):
        """Invoice lines must not appear in recognized_amount,
        and recognition lines must not appear in invoiced_amount."""
        po = self._create_obligation(perf_type="income", total_amount=1000)

        # Post an invoice linked to the obligation
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
            date="2026-01-01",
        )

        # Recognize 0: produces a deferral entry (debit inc_pl 1000, credit BS 1000)
        self._create_wizard(
            po,
            amount=0,
            date="2026-01-31",
            description="Jan",
        ).action_confirm()
        self.env["account.move.line"].flush_model()
        self.env["account.move"].flush_model()

        lines = self.env["perf.obligation.schedule.income"].search(
            [("perf_obligation_id", "=", po.id)],
            order="date asc, move_id asc",
        )
        # Two rows: one for the invoice, one for the recognition entry
        self.assertEqual(len(lines), 2)

        invoice_line = lines.filtered(
            lambda line: line.move_id.journal_id == self.sale_journal
        )
        reco_line = lines.filtered(
            lambda line: line.move_id.journal_id == self.reco_journal
        )

        self.assertAlmostEqual(invoice_line.invoiced_amount, 1000)
        self.assertAlmostEqual(invoice_line.recognized_amount, 0)

        self.assertAlmostEqual(reco_line.recognized_amount, -1000)
        self.assertAlmostEqual(reco_line.invoiced_amount, 0)
        self.assertAlmostEqual(reco_line.deferred_accrued_amount, -1000)

    def test_schedule_expense_bill_and_reco_are_segregated(self):
        """Bill lines must not appear in recognized_amount,
        and recognition lines must not appear in billed_amount."""
        po = self._create_obligation(perf_type="expense", total_amount=1000)

        # Post a bill linked to the obligation
        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 1000, False),
                (self.expense_account, 1000, 0, po),
            ],
            date="2026-01-01",
        )

        # Recognize 0: produces a deferral entry (credit exp_pl 1000, debit BS 1000)
        self._create_wizard(
            po,
            amount=0,
            date="2026-01-31",
            description="Jan",
        ).action_confirm()
        self.env["account.move.line"].flush_model()
        self.env["account.move"].flush_model()

        lines = self.env["perf.obligation.schedule.expense"].search(
            [("perf_obligation_id", "=", po.id)],
            order="date asc, move_id asc",
        )
        self.assertEqual(len(lines), 2)

        bill_line = lines.filtered(
            lambda line: line.move_id.journal_id == self.purchase_journal
        )
        reco_line = lines.filtered(
            lambda line: line.move_id.journal_id == self.exp_reco_journal
        )

        self.assertAlmostEqual(bill_line.billed_amount, 1000)
        self.assertAlmostEqual(bill_line.recognized_amount, 0)

        self.assertAlmostEqual(reco_line.recognized_amount, -1000)
        self.assertAlmostEqual(reco_line.billed_amount, 0)
        self.assertAlmostEqual(reco_line.deferred_accrued_amount, -1000)
