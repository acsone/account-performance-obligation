# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from odoo.exceptions import ValidationError

from .common import PerfObligationDatesCommon


class TestForecast(PerfObligationDatesCommon):
    def _mock_today(self, today):
        """Return a context manager that mocks fields.Date.context_today.

        Only needed to allow posting moves with auto_post='at_date'
        whose date is in the future relative to the real today.
        """
        return patch(
            "odoo.fields.Date.context_today",
            return_value=today,
        )

    # =========================================================
    # Supports forecast
    # =========================================================

    def test_supports_forecast_false_without_method(self):
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_forecast())

    def test_supports_forecast_true_with_daily(self):
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self.assertTrue(po._supports_forecast())

    def test_supports_forecast_false_without_end_date(self):
        """Method configured but no end_date -> no forecast support."""
        po = self._create_obligation(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        # No recognition method set
        self.assertFalse(po._supports_forecast())

    # =========================================================
    # Forecast dates
    # =========================================================

    def test_forecast_dates_quarterly(self):
        """3-month obligation generates 3 month-end dates."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        dates = po._get_forecast_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_forecast_dates_mid_month_start(self):
        """Start mid-month still gets month-end for first month."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 15),
            end_date=date(2026, 3, 31),
        )
        dates = po._get_forecast_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_forecast_dates_end_before_month_end(self):
        """End date before month-end uses end_date as last date."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 15),
        )
        dates = po._get_forecast_dates()
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 15)],
        )

    def test_forecast_dates_single_month(self):
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 31),
        )
        dates = po._get_forecast_dates()
        self.assertEqual(dates, [date(2026, 3, 31)])

    def test_forecast_dates_leap_year(self):
        """February in a leap year ends on 29th."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2028, 1, 1),
            end_date=date(2028, 2, 29),
        )
        dates = po._get_forecast_dates()
        self.assertEqual(
            dates,
            [date(2028, 1, 31), date(2028, 2, 29)],
        )

    def test_forecast_dates_year_boundary(self):
        """Dates spanning a year boundary."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 11, 1),
            end_date=date(2027, 2, 28),
        )
        dates = po._get_forecast_dates()
        self.assertEqual(
            dates,
            [
                date(2026, 11, 30),
                date(2026, 12, 31),
                date(2027, 1, 31),
                date(2027, 2, 28),
            ],
        )

    def test_forecast_dates_skips_posted_months(self):
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

        # Mock today to the move date so Odoo allows posting
        with self._mock_today(date(2026, 1, 31)):
            move.action_post()

        # forecast_start = max(Jan 1, Jan 31) = Jan 31
        # -> skip Jan month-end (== forecast_start)
        dates = po._get_forecast_dates()
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

    def test_forecast_dates_empty_when_fully_recognized(self):
        """Returns empty list when last posted entry covers end_date."""
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
        with self._mock_today(date(2026, 3, 31)):
            move.action_post()

        dates = po._get_forecast_dates()
        self.assertEqual(dates, [])

    # =========================================================
    # Forecast generation
    # =========================================================

    def test_generate_forecast_income_no_invoice(self):
        """Generate forecast for income with no prior invoice."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        self.assertEqual(len(draft_moves), 3)

        dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

        for move in draft_moves:
            self.assertEqual(move.state, "draft")
            self.assertEqual(move.auto_post, "at_date")
            self.assertEqual(move.journal_id, self.reco_journal)
            for line in move.line_ids:
                self.assertEqual(line.perf_obligation_id, po)

    def test_generate_forecast_expense(self):
        """Generate forecast entries for expense obligation."""
        po = self._create_obligation(
            perf_type="expense",
            total_amount=600.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 2, 28),
        )
        po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        self.assertEqual(len(draft_moves), 2)

        for move in draft_moves:
            self.assertEqual(move.journal_id, self.exp_reco_journal)

    def test_generate_forecast_with_invoice_at_beginning(self):
        """Forecast with invoice posted at the beginning generates
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
        po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        self.assertEqual(len(draft_moves), 3)

    def test_generate_forecast_replaces_existing_drafts(self):
        """Calling action_generate_forecast twice replaces previous drafts."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        po.action_generate_forecast()
        first_move_ids = set(po._get_draft_recognition_moves().ids)

        po.action_generate_forecast()
        second_move_ids = set(po._get_draft_recognition_moves().ids)

        self.assertFalse(first_move_ids & second_move_ids)
        self.assertEqual(len(second_move_ids), 3)

    def test_generate_forecast_preserves_posted_moves(self):
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

        # Mock today to the move date so Odoo allows posting
        with self._mock_today(date(2026, 1, 31)):
            posted_move.action_post()

        # Posted move still exists
        self.assertTrue(posted_move.exists())
        self.assertEqual(posted_move.state, "posted")

        # Regenerate forecast
        po.action_generate_forecast()

        # Draft moves generated for remaining months only
        draft_moves = po._get_draft_recognition_moves()
        draft_dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            draft_dates,
            [date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_generate_forecast_unsupported_raises(self):
        """Forecast on obligation without method raises."""
        po = self._create_obligation(total_amount=1000.0)
        with self.assertRaises(ValidationError) as ctx:
            po.action_generate_forecast()
        self.assertRegex(str(ctx.exception), r"Forecast generation is not supported")

    def test_forecast_ref_contains_obligation_name(self):
        """Forecast move ref contains the obligation reference."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        self.assertEqual(len(draft_moves), 1)
        self.assertIn(po.name, draft_moves.ref)

    def test_generate_forecast_all_months(self):
        """All months from start_date to end_date are generated."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        draft_dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            draft_dates,
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )
