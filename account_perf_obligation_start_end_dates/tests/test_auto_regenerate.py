# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from .common import PerfObligationDatesCommon


class TestAutoRegenerate(PerfObligationDatesCommon):
    """Integration tests for the flag-based schedule regeneration
    mechanism with the daily pro-rata method.

    These tests cover the full chain:

    - operations on the obligation or on linked move lines flag the
      obligation via ``schedule_needs_regeneration``
    - calling ``_process_pending_regenerations()`` rebuilds the draft
      schedule and clears the flag
    - posted recognition entries are preserved across regenerations
    - the recursion guard prevents marking during regeneration itself
    """

    def _mock_today(self, today):
        return patch(
            "odoo.fields.Date.context_today",
            return_value=today,
        )

    def _make_po(self, **overrides):
        defaults = dict(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        defaults.update(overrides)
        return self._create_obligation(**defaults)

    # =========================================================
    # Trigger field list
    # =========================================================

    def test_trigger_fields_includes_dates(self):
        """The dates module extends the trigger field list with
        start_date and end_date."""
        po = self._make_po()
        fields_list = po._get_recognition_trigger_fields()
        self.assertIn("start_date", fields_list)
        self.assertIn("end_date", fields_list)
        self.assertIn("total_amount", fields_list)
        self.assertIn("recognition_at_date_method", fields_list)

    # =========================================================
    # Marking on create
    # =========================================================

    def test_create_with_supported_config_marks(self):
        """Creating an obligation with a complete configuration sets
        the schedule_needs_regeneration flag."""
        po = self._make_po()
        self.assertTrue(po.schedule_needs_regeneration)
        # No drafts yet: regeneration hasn't run
        self.assertFalse(po._get_draft_schedule_moves())

    def test_create_without_full_config_does_not_mark(self):
        """Creating an obligation without dates/method does not flag it."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po.schedule_needs_regeneration)

    # =========================================================
    # Marking on perf.obligation field changes
    # =========================================================

    def test_change_total_amount_marks(self):
        """Changing total_amount sets the flag."""
        po = self._make_po()
        po.schedule_needs_regeneration = False
        po.total_amount = 1800.0
        self.assertTrue(po.schedule_needs_regeneration)

    def test_change_start_date_marks(self):
        """Changing start_date sets the flag."""
        po = self._make_po()
        po.schedule_needs_regeneration = False
        po.start_date = date(2026, 2, 1)
        self.assertTrue(po.schedule_needs_regeneration)

    def test_change_end_date_marks(self):
        """Changing end_date sets the flag."""
        po = self._make_po()
        po.schedule_needs_regeneration = False
        po.end_date = date(2026, 2, 28)
        self.assertTrue(po.schedule_needs_regeneration)

    def test_change_unrelated_field_does_not_mark(self):
        """Writing an unrelated field does not flag the obligation."""
        po = self._make_po()
        po.schedule_needs_regeneration = False
        po.description = "Some unrelated change"
        self.assertFalse(po.schedule_needs_regeneration)

    # =========================================================
    # Marking on linked move-line changes
    # =========================================================

    def test_post_invoice_marks(self):
        """Posting an invoice line linked to the obligation flags it."""
        po = self._make_po()
        po.schedule_needs_regeneration = False
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-01-01",
        )
        self.assertTrue(po.schedule_needs_regeneration)

    def test_modify_invoice_line_marks(self):
        """Modifying an invoice line linked to the obligation flags it."""
        po = self._make_po()
        invoice = self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-01-01",
        )
        po.schedule_needs_regeneration = False

        income_line = self._filter_lines(invoice.line_ids, self.income_account)
        income_line.with_context(check_move_validity=False).write(
            {"name": "Updated label"}
        )

        self.assertTrue(po.schedule_needs_regeneration)

    def test_unlink_obligation_from_line_marks_previous(self):
        """Removing perf_obligation_id from a line flags the previously-
        linked obligation."""
        po = self._make_po()
        invoice = self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 900, 0, False),
                (self.income_account, 0, 900, po),
            ],
            date="2026-01-01",
        )
        po.schedule_needs_regeneration = False

        income_line = self._filter_lines(invoice.line_ids, self.income_account)
        income_line.with_context(check_move_validity=False).write(
            {"perf_obligation_id": False}
        )

        self.assertTrue(po.schedule_needs_regeneration)

    # =========================================================
    # Processing pending regenerations
    # =========================================================

    def test_process_pending_generates_schedule(self):
        """_process_pending_regenerations builds the draft schedule
        for a flagged obligation."""
        po = self._make_po()
        self.assertTrue(po.schedule_needs_regeneration)

        po._process_pending_regenerations()

        # Flag cleared
        self.assertFalse(po.schedule_needs_regeneration)
        # Drafts generated
        drafts = po._get_draft_schedule_moves()
        self.assertEqual(len(drafts), 3)
        self.assertEqual(
            sorted(drafts.mapped("date")),
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_process_pending_replaces_existing_drafts(self):
        """Running processing twice replaces previous drafts."""
        po = self._make_po()
        po._process_pending_regenerations()
        first_ids = set(po._get_draft_schedule_moves().ids)
        self.assertEqual(len(first_ids), 3)

        # Trigger another regeneration
        po.total_amount = 1800.0
        self.assertTrue(po.schedule_needs_regeneration)

        po._process_pending_regenerations()
        second_ids = set(po._get_draft_schedule_moves().ids)

        self.assertFalse(first_ids & second_ids)
        self.assertEqual(len(second_ids), 3)
        self.assertFalse(po.schedule_needs_regeneration)

    def test_process_pending_preserves_posted_moves(self):
        """Posted recognition entries are preserved across regeneration."""
        po = self._make_po()
        po._process_pending_regenerations()

        jan_draft = po._get_draft_schedule_moves().filtered(
            lambda m: m.date == date(2026, 1, 31)
        )
        self.assertTrue(jan_draft)
        with self._mock_today(date(2026, 1, 31)):
            jan_draft.action_post()
        self.assertEqual(jan_draft.state, "posted")

        # Trigger regeneration via total_amount change
        po.total_amount = 1200.0
        self.assertTrue(po.schedule_needs_regeneration)

        po._process_pending_regenerations()

        # Posted move untouched
        self.assertTrue(jan_draft.exists())
        self.assertEqual(jan_draft.state, "posted")

        # Drafts only for Feb and Mar
        new_drafts = po._get_draft_schedule_moves()
        self.assertEqual(
            sorted(new_drafts.mapped("date")),
            [date(2026, 2, 28), date(2026, 3, 31)],
        )
        self.assertFalse(po.schedule_needs_regeneration)

    def test_action_process_pending_regenerations(self):
        """The list-view action runs the processing on the recordset."""
        po = self._make_po()
        self.assertTrue(po.schedule_needs_regeneration)

        po.action_process_pending_regenerations()

        self.assertFalse(po.schedule_needs_regeneration)
        self.assertEqual(len(po._get_draft_schedule_moves()), 3)

    # =========================================================
    # Recursion guard
    # =========================================================

    def test_no_recursion_during_regeneration(self):
        """While _regenerate_schedule runs, it creates draft moves
        whose lines are linked to the obligation. The
        perf_obligation_in_regeneration context flag must prevent
        these creations from re-flagging the obligation."""
        po = self._make_po()
        po._process_pending_regenerations()

        # Flag is cleared and exactly 3 drafts exist
        self.assertFalse(po.schedule_needs_regeneration)
        self.assertEqual(len(po._get_draft_schedule_moves()), 3)
