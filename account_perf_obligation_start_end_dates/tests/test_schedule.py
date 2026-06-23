# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.exceptions import ValidationError

from .common import PerfObligationDatesCommon


class TestSchedule(PerfObligationDatesCommon):
    # =========================================================
    # Supports schedule
    # =========================================================

    def test_supports_schedule_false_without_method(self):
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_schedule())
        self.assertFalse(po.supports_schedule)

    def test_supports_schedule_true_with_daily(self):
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self.assertTrue(po._supports_schedule())
        self.assertTrue(po.supports_schedule)

    def test_supports_schedule_false_without_end_date(self):
        """Method configured but no end_date -> no schedule support."""
        po = self._create_obligation(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        # No recognition method set
        self.assertFalse(po._supports_schedule())
        self.assertFalse(po.supports_schedule)

    def test_supports_schedule_false_without_start_date(self):
        """Method and end_date set but no start_date -> no schedule support."""
        po = self._create_obligation(
            end_date=date(2026, 3, 31),
        )
        po.recognition_at_date_method = False
        self.assertFalse(po._supports_schedule())
        self.assertFalse(po.supports_schedule)

    # =========================================================
    # Schedule dates
    # =========================================================

    def test_schedule_dates_quarterly(self):
        """3-month obligation generates 3 month-end dates."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_schedule_dates_mid_month_start(self):
        """Start mid-month still gets month-end for first month."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 3, 31),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_schedule_dates_end_before_month_end(self):
        """End date before month-end uses end_date as last date."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 15),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_schedule_dates_single_month(self):
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(dates, [date(2026, 3, 31)])

    def test_schedule_dates_leap_year(self):
        """February in a leap year ends on 29th."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2028, 1, 1),
            end_date=date(2028, 2, 29),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [date(2028, 1, 31), date(2028, 2, 29)],
        )

    def test_schedule_dates_year_boundary(self):
        """Dates spanning a year boundary."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 11, 1),
            end_date=date(2027, 2, 28),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [
                date(2026, 11, 30),
                date(2026, 12, 31),
                date(2027, 1, 31),
                date(2027, 2, 28),
            ],
        )

    def test_schedule_dates_skips_posted_months(self):
        """Months with posted recognition entries are skipped."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=600.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        # Manually recognize Jan and post
        wizard = self._create_wizard(
            po,
            amount=po._compute_amount_to_recognize_at_date(date(2026, 1, 31)),
            date="2026-01-31",
            description="Jan",
        )
        result = wizard.action_confirm()
        move = self.env["account.move"].browse(result["res_id"])
        move.action_post()
        # schedule_start = last_posted = Jan 31 (no max with start_date now)
        # -> skip Jan month-end (== schedule_start)
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [
                date(2026, 2, 28),
                date(2026, 3, 31),
                date(2026, 4, 30),
                date(2026, 5, 31),
                date(2026, 6, 30),
            ],
        )

    def test_schedule_dates_when_fully_recognized(self):
        """Returns next month date when last posted entry covers end_date."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        # Recognize up to end_date and post
        wizard = self._create_wizard(
            po,
            amount=po._compute_amount_to_recognize_at_date(date(2026, 3, 31)),
            date="2026-03-31",
            description="Full",
        )
        result = wizard.action_confirm()
        move = self.env["account.move"].browse(result["res_id"])
        move.action_post()
        dates = po._get_schedule_dates()
        self.assertEqual(dates, [date(2026, 4, 30)])

    # =========================================================
    # Schedule generation
    # =========================================================

    def test_generate_schedule_income_no_invoice(self):
        """Generate schedule for income with no prior invoice."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        po.action_generate_schedule()

        draft_moves = po._get_draft_schedule_moves()
        self.assertEqual(len(draft_moves), 3)

        dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

        for move in draft_moves:
            self.assertEqual(move.state, "draft")
            self.assertEqual(move.journal_id, self.reco_journal)
            for line in move.line_ids:
                self.assertEqual(line.perf_obligation_id, po)

    def test_generate_schedule_expense(self):
        """Generate schedule entries for expense obligation."""
        po = self._create_obligation(
            perf_type="expense",
            total_amount=600.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 28),
        )
        po.action_generate_schedule()

        draft_moves = po._get_draft_schedule_moves()
        self.assertEqual(len(draft_moves), 2)

        for move in draft_moves:
            self.assertEqual(move.journal_id, self.exp_reco_journal)

    def test_generate_schedule_with_invoice_at_beginning(self):
        """Schedule with invoice posted at the beginning generates
        deferral entries."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-01-01",
        )
        po.action_generate_schedule()

        draft_moves = po._get_draft_schedule_moves()
        self.assertEqual(len(draft_moves), 3)

    def test_generate_schedule_replaces_existing_drafts(self):
        """Calling action_generate_schedule twice replaces previous drafts."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        po.action_generate_schedule()
        first_move_ids = set(po._get_draft_schedule_moves().ids)

        po.action_generate_schedule()
        second_move_ids = set(po._get_draft_schedule_moves().ids)

        self.assertFalse(first_move_ids & second_move_ids)
        self.assertEqual(len(second_move_ids), 3)

    def test_generate_schedule_preserves_posted_moves(self):
        """Posted recognition moves are not deleted on regeneration."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        # Manually recognize Jan and post it
        wizard = self._create_wizard(
            po,
            amount=po._compute_amount_to_recognize_at_date(date(2026, 1, 31)),
            date="2026-01-31",
            description="Jan manual",
        )
        result = wizard.action_confirm()
        posted_move = self.env["account.move"].browse(result["res_id"])
        posted_move.action_post()
        # Posted move still exists
        self.assertTrue(posted_move.exists())
        self.assertEqual(posted_move.state, "posted")

        # Regenerate schedule
        po.action_generate_schedule()

        # Draft moves generated for remaining months only
        draft_moves = po._get_draft_schedule_moves()
        draft_dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            draft_dates,
            [date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_generate_schedule_unsupported_raises(self):
        """Schedule on obligation without method raises."""
        po = self._create_obligation(total_amount=1000.0)
        with self.assertRaisesRegex(
            ValidationError, r"Schedule generation is not supported"
        ):
            po.action_generate_schedule()

    def test_schedule_ref_contains_obligation_name(self):
        """Schedule move ref contains the obligation reference."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        po.action_generate_schedule()

        draft_moves = po._get_draft_schedule_moves()
        self.assertEqual(len(draft_moves), 1)
        self.assertIn(po.name, draft_moves.ref)

    def test_generate_schedule_all_months(self):
        """All months from start_date to end_date are generated."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        po.action_generate_schedule()

        draft_moves = po._get_draft_schedule_moves()
        draft_dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            draft_dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_schedule_dates_with_invoice_before_start(self):
        """Schedule starts at min(first move date, start_date) when no
        posted recognition exists.

        An invoice posted before start_date should extend the schedule
        backwards so that the early period gets a recognition entry too.
        """
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
        )
        # Invoice posted in January, before start_date
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-01-15",
        )
        dates = po._get_schedule_dates()
        # schedule_start = min(Jan 15, Feb 1) = Jan 15
        # -> Jan month-end is included
        self.assertEqual(
            dates,
            [
                date(2026, 1, 31),
                date(2026, 2, 28),
                date(2026, 3, 31),
                date(2026, 4, 30),
            ],
        )

    def test_schedule_dates_with_invoice_after_end(self):
        """Schedule ends at max(last move date, end_date).

        An invoice posted after end_date should extend the schedule
        forward so that the late period gets a recognition entry too.
        """
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 28),
        )
        # Invoice posted in March, after end_date
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-03-15",
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_schedule_dates_posted_reco_takes_precedence_over_early_invoice(
        self,
    ):
        """When a posted recognition exists, schedule_start uses it
        directly and ignores any earlier movement.

        This avoids regenerating drafts for periods already covered
        by posted entries, even if there are movements before start_date.
        """
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 4, 30),
        )
        # Invoice before start_date
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-01-15",
        )
        # Posted reco for Feb 28
        wizard = self._create_wizard(
            po,
            amount=po._compute_amount_to_recognize_at_date(date(2026, 2, 28)),
            date="2026-02-28",
            description="Feb reco",
        )
        result = wizard.action_confirm()
        move = self.env["account.move"].browse(result["res_id"])
        move.action_post()
        dates = po._get_schedule_dates()
        # schedule_start = last_posted = Feb 28 (NOT Jan 15)
        # -> Jan month-end NOT included, Feb 28 skipped (== start)
        self.assertEqual(
            dates,
            [date(2026, 3, 31), date(2026, 4, 30)],
        )

    def test_schedule_dates_start_on_last_day_of_month(self):
        """Start date on the last day of a month must not skip that month."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 5, 31),
            end_date=date(2026, 6, 2),
        )
        dates = po._get_schedule_dates()
        self.assertEqual(
            dates,
            [date(2026, 5, 31), date(2026, 6, 30)],
        )

    def test_schedule_dates_end_date_before_last_posted_generates_corrective(self):
        """When end_date is pulled back before last_posted, a corrective
        entry is generated."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=1000.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 12, 31),
        )
        for reco_date in [date(2026, 4, 30), date(2026, 5, 31)]:
            wizard = self._create_wizard(
                po,
                amount=po._compute_amount_to_recognize_at_date(reco_date),
                date=str(reco_date),
                description=f"Reco {reco_date}",
            )
            result = wizard.action_confirm()
            move = self.env["account.move"].browse(result["res_id"])
            move.action_post()
        po.end_date = date(2026, 4, 15)
        dates = po._get_schedule_dates()
        self.assertEqual(dates, [date(2026, 6, 30)])
