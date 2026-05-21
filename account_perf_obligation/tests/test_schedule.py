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
