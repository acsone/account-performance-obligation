# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.exceptions import UserError

from .common import PerfObligationDatesCommon


class TestPostponeNotInService(PerfObligationDatesCommon):
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
        po._postpone_not_in_service_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 11, 1))
        self.assertEqual(po.end_date, date(2026, 3, 31))
        # Postponing does not put the obligation in service.
        self.assertTrue(po.not_in_service)
        self.assertEqual(po.state, "open")

    def test_postpone_ignores_obligation_starting_after_the_date(self):
        po = self._make_po(start_date=date(2025, 12, 1))
        po._postpone_not_in_service_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 12, 1))

    def test_postpone_ignores_obligation_in_service(self):
        po = self._make_po(not_in_service=False)
        po._postpone_not_in_service_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 10, 12))

    def test_postpone_ignores_done_obligation(self):
        """A done obligation is locked: it is skipped instead of raising on
        the write lock."""
        po = self._make_po(state="done")
        po._postpone_not_in_service_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 10, 12))

    def test_postpone_after_end_date_raises(self):
        po = self._make_po(end_date=date(2025, 10, 31))
        with self.assertRaisesRegex(UserError, "after its end date"):
            po._postpone_not_in_service_obligations(date(2025, 10, 31))

    def test_postpone_one_day_obligation_moves_both_dates(self):
        """When start date equals end date, the end date is postponed too."""
        po = self._make_po(start_date=date(2025, 10, 12), end_date=date(2025, 10, 12))
        po._postpone_not_in_service_obligations(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 11, 1))
        self.assertEqual(po.end_date, date(2025, 11, 1))
        self.assertTrue(po.not_in_service)

    # =========================================================
    # Through the recognition posting run
    # =========================================================

    def test_post_all_postpones_obligation_not_in_service(self):
        """Posting recognition entries postpones the start date of an
        obligation not in service, regenerates its schedule and posts
        nothing for it."""
        po = self._make_po()
        po._regenerate_schedule()
        self.env["perf.obligation"]._post_all_recognition_moves(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 11, 1))
        self.assertFalse(po.schedule_needs_regeneration)
        drafts = po._get_draft_schedule_moves()
        # The schedule restarts from the postponed start date.
        self.assertEqual(
            sorted(drafts.mapped("date"))[0],
            date(2025, 11, 30),
        )
        self.assertNotIn(date(2025, 10, 31), drafts.mapped("date"))
        # Nothing is marked for auto-posting.
        self.assertTrue(all(move.auto_post == "no" for move in drafts))

    def test_post_all_does_not_postpone_obligation_in_service(self):
        po = self._make_po(not_in_service=False)
        self.env["perf.obligation"]._post_all_recognition_moves(date(2025, 10, 31))
        self.assertEqual(po.start_date, date(2025, 10, 12))
