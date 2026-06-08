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
        po._recognize(100, "2026-01-31", "Jan")
        # The schedule is an SQL view based on account.move.line.
        # Flush accounting lines before querying the view.
        self.env["account.move.line"].flush_model()
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

    def test_income_monthly_aggregates_same_month(self):
        """An invoice and a recognition entry in the same month must produce
        a single monthly schedule line whose amounts are the sum of both moves.
        """
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        # Invoice: 300 posted on 2026-01-15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
            date="2026-01-15",
        )
        # Recognition entry: recognize 400 cumulatively on 2026-01-31
        # (invoiced 300 already, so recognition move adds 100 deferred)
        po._recognize(400, date="2026-01-31", description="Jan reco")
        self.env["account.move.line"].flush_model()
        monthly_lines = self.env["perf.obligation.schedule.income.monthly"].search(
            [("perf_obligation_id", "=", po.id)],
        )
        # Both moves are in January 2026 → exactly one monthly line
        self.assertEqual(len(monthly_lines), 1)
        line = monthly_lines[0]
        self.assertEqual(line.month, "2026-01")
        # Invoiced = 300 (from the sale move), recognized = 400 (cumulative)
        self.assertAlmostEqual(line.invoiced_amount, 300, places=2)
        self.assertAlmostEqual(line.recognized_amount, 400, places=2)
        # deferred = recognized - invoiced = 100
        self.assertAlmostEqual(line.deferred_accrued_amount, 100, places=2)
        # Running totals equal the monthly amounts (single month)
        self.assertAlmostEqual(line.total_invoiced_amount, 300, places=2)
        self.assertAlmostEqual(line.total_recognized_amount, 400, places=2)
        self.assertAlmostEqual(line.total_deferred_accrued_amount, 100, places=2)

    def test_income_monthly_two_months_produce_two_lines(self):
        """Moves spread across two months must produce two distinct monthly lines
        with correct running totals.
        """
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        # January: invoice 300
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
            date="2026-01-31",
        )
        # February: invoice 200 more
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 200, 0, False),
                (self.income_account, 0, 200, po),
            ],
            date="2026-02-28",
        )
        monthly_lines = self.env["perf.obligation.schedule.income.monthly"].search(
            [("perf_obligation_id", "=", po.id)],
            order="id",
        )
        self.assertEqual(len(monthly_lines), 2)
        jan, feb = monthly_lines
        self.assertEqual(jan.month, "2026-01")
        self.assertEqual(feb.month, "2026-02")
        # January totals
        self.assertAlmostEqual(jan.invoiced_amount, 300, places=2)
        self.assertAlmostEqual(jan.total_invoiced_amount, 300, places=2)
        # February totals: monthly 200, cumulative 500
        self.assertAlmostEqual(feb.invoiced_amount, 200, places=2)
        self.assertAlmostEqual(feb.total_invoiced_amount, 500, places=2)

    def test_income_monthly_mixed_state(self):
        """A month containing both a posted and a draft move must show
        state 'mixed'.
        """
        po = self._create_obligation(perf_type="income", total_amount=1000.0)
        # Posted invoice
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
            date="2026-01-15",
        )
        # Draft recognition entry (not posted)
        po._recognize(500, date="2026-01-31", description="Jan reco draft")
        self.env["account.move.line"].flush_model()
        monthly_lines = self.env["perf.obligation.schedule.income.monthly"].search(
            [("perf_obligation_id", "=", po.id)],
        )
        self.assertEqual(len(monthly_lines), 1)
        self.assertEqual(monthly_lines.state, "mixed")
