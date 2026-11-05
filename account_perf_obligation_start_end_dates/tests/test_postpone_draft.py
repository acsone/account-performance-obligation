# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.exceptions import UserError

from .common import PerfObligationDatesCommon


class TestPostponeDraft(PerfObligationDatesCommon):
    def _make_po(self, **overrides):
        defaults = dict(
            perf_type="income",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2025, 10, 12),
            end_date=date(2026, 3, 31),
        )
        defaults.update(overrides)
        return self._create_obligation(**defaults)

    def test_postpone_moves_start_date_to_first_day_of_next_month(self):
        po = self._make_po()
        po._postpone_draft_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 11, 1))
        self.assertEqual(po.end_date, date(2026, 3, 31))
        self.assertEqual(po.state, "draft")

    def test_postpone_ignores_obligation_starting_after_the_date(self):
        po = self._make_po(start_date=date(2025, 12, 1))
        po._postpone_draft_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 12, 1))

    def test_postpone_ignores_obligation_in_progress(self):
        po = self._make_po(state="in_progress")
        po._postpone_draft_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 10, 12))

    def test_postpone_after_end_date_raises(self):
        po = self._make_po(end_date=date(2025, 10, 31))
        with self.assertRaisesRegex(UserError, "after its end date"):
            po._postpone_draft_obligations(date(2025, 10, 31))

    def test_postpone_one_day_obligation_moves_both_dates(self):
        """When start date equals end date, the end date is postponed too."""
        po = self._make_po(start_date=date(2025, 10, 12), end_date=date(2025, 10, 12))
        po._postpone_draft_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 11, 1))
        self.assertEqual(po.end_date, date(2025, 11, 1))
        self.assertEqual(po.state, "draft")
