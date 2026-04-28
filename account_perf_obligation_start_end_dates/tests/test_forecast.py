# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from .common import PerfObligationDatesCommon


class TestForecast(PerfObligationDatesCommon):
    def _mock_today(self, today):
        """Return a context manager that mocks fields.Date.context_today."""
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
            dates = po._get_forecast_dates()
        self.assertEqual(dates, [date(2026, 3, 31)])

    def test_forecast_dates_leap_year(self):
        """February in a leap year ends on 29th."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2028, 1, 1),
            end_date=date(2028, 2, 29),
        )
        with self._mock_today(date(2027, 12, 1)):
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
        with self._mock_today(date(2026, 10, 1)):
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

    def test_forecast_dates_skips_past_months(self):
        """Months where month-end is before or on today are skipped."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        with self._mock_today(date(2026, 3, 15)):
            dates = po._get_forecast_dates()
        self.assertEqual(
            dates,
            [
                date(2026, 3, 31),
                date(2026, 4, 30),
                date(2026, 5, 31),
                date(2026, 6, 30),
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
        with self._mock_today(date(2025, 12, 1)):
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

        # Today is Jan 15, but last posted is Jan 31
        # forecast_start = max(Jan 15, Jan 31, Jan 1) = Jan 31
        # -> skip Jan month-end (== forecast_start)
        with self._mock_today(date(2026, 1, 15)):
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

    def test_forecast_dates_empty_when_all_past(self):
        """Returns empty list when end_date is in the past."""
        po = self._create_obligation(
            recognition_at_date_method="daily",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 3, 31),
        )
        with self._mock_today(date(2026, 1, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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
        with self._mock_today(date(2025, 12, 1)):
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

        # Now generate forecast (today still before obligation end)
        with self._mock_today(date(2025, 12, 1)):
            po.action_generate_forecast()

        # Draft moves generated for remaining months only
        draft_moves = po._get_draft_recognition_moves()
        draft_dates = sorted(draft_moves.mapped("date"))
        self.assertEqual(
            draft_dates,
            [date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_forecast_ref_contains_obligation_name(self):
        """Forecast move ref contains the obligation reference."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        with self._mock_today(date(2025, 12, 1)):
            po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        self.assertEqual(len(draft_moves), 1)
        self.assertIn(po.name, draft_moves.ref)

    def test_generate_forecast_partial_month_coverage(self):
        """Today is mid-month: current month-end is still included."""
        po = self._create_obligation(
            perf_type="income",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        with self._mock_today(date(2026, 2, 15)):
            po.action_generate_forecast()

        draft_moves = po._get_draft_recognition_moves()
        draft_dates = sorted(draft_moves.mapped("date"))
        # Jan is past, Feb 28 > Feb 15 so included, Mar included
        self.assertEqual(
            draft_dates,
            [date(2026, 2, 28), date(2026, 3, 31)],
        )
