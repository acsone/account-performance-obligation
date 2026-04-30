# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


from .common import PerfObligationCommon


class TestSchedule(PerfObligationCommon):
    def test_expense_schedule_without_bill_has_zero_invoiced_amount(self):
        """Recognizing expense before receiving the bill creates an accrual,
        but the invoiced/billed amount must remain zero.
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
        self.assertAlmostEqual(schedule_line.deferred_accrued_amount, -100)

        # No vendor bill exists yet, so invoiced/billed must be zero.
        self.assertAlmostEqual(schedule_line.invoiced_amount, 0)
        self.assertAlmostEqual(schedule_line.total_invoiced_amount, 0)
        self.assertAlmostEqual(schedule_line.total_recognized_amount, 100)
        self.assertAlmostEqual(schedule_line.total_deferred_accrued_amount, -100)
