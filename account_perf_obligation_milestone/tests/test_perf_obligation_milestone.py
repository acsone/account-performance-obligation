# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError

from odoo.addons.account_perf_obligation_start_end_dates.tests.common import (
    PerfObligationDatesCommon,
)


class TestPerfObligationMilestone(PerfObligationDatesCommon):
    def _mock_today(self, today):
        return patch("odoo.fields.Date.context_today", return_value=today)

    def _make_po(self, **overrides):
        defaults = dict(
            perf_type="income",
            total_amount=1200.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        defaults.update(overrides)
        return self._create_obligation(**defaults)

    def _create_milestones(self, po, *date_amounts):
        return self.env["perf.obligation.milestone"].create(
            [
                {
                    "perf_obligation_id": po.id,
                    "date": milestone_date,
                    "amount": amount,
                }
                for milestone_date, amount in date_amounts
            ]
        )

    def _recognized_at(self, po, at_date):
        """Cumulative income booked by recognition entries (any state) up to
        ``at_date``. No invoice is posted in these tests, so the recognition
        P&L account only holds recognition entries."""
        lines = self.env["account.move.line"].search(
            [
                ("perf_obligation_id", "=", po.id),
                ("account_id", "=", self.inc_pl.id),
                ("date", "<=", at_date),
            ]
        )
        return sum(lines.mapped("credit")) - sum(lines.mapped("debit"))

    # =========================================================
    # Amount computation
    # =========================================================

    def test_no_milestone_is_plain_daily(self):
        po = self._make_po()
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 6, 30)), 595.07
        )

    def test_amounts_between_milestones(self):
        po = self._make_po()
        self._create_milestones(
            po, (date(2026, 6, 30), 500.0), (date(2026, 11, 30), 1000.0)
        )
        compute = po._compute_amount_to_recognize_at_date
        self.assertEqual(compute(date(2025, 12, 31)), 0.0)
        self.assertEqual(compute(date(2026, 1, 1)), 2.76)
        self.assertEqual(compute(date(2026, 6, 30)), 500.0)
        self.assertEqual(compute(date(2026, 9, 1)), 705.88)
        self.assertEqual(compute(date(2026, 11, 30)), 1000.0)
        self.assertEqual(compute(date(2026, 12, 31)), 1200.0)
        self.assertEqual(compute(date(2027, 6, 15)), 1200.0)

    def test_decreasing_milestones(self):
        """Income can be de-recognized: milestone amounts may decrease."""
        po = self._make_po()
        self._create_milestones(
            po, (date(2026, 6, 30), 800.0), (date(2026, 11, 30), 500.0)
        )
        compute = po._compute_amount_to_recognize_at_date
        self.assertEqual(compute(date(2026, 6, 30)), 800.0)
        self.assertEqual(compute(date(2026, 9, 1)), 676.47)
        self.assertEqual(compute(date(2026, 11, 30)), 500.0)
        self.assertEqual(compute(date(2026, 12, 31)), 1200.0)

    def test_milestone_on_end_date_is_overridden_by_total(self):
        po = self._make_po()
        self._create_milestones(po, (date(2026, 12, 31), 800.0))
        compute = po._compute_amount_to_recognize_at_date
        self.assertEqual(compute(date(2026, 12, 30)), 1196.71)
        self.assertEqual(compute(date(2026, 12, 31)), 1200.0)

    def test_negative_total_amount(self):
        po = self._make_po(total_amount=-1200.0)
        self._create_milestones(po, (date(2026, 6, 30), -500.0))
        compute = po._compute_amount_to_recognize_at_date
        self.assertEqual(compute(date(2026, 6, 30)), -500.0)
        self.assertEqual(compute(date(2026, 12, 31)), -1200.0)

    # =========================================================
    # Out of period / method
    # =========================================================

    def test_out_of_period_milestones_are_ignored(self):
        po = self._make_po()
        milestones = self._create_milestones(
            po,
            (date(2026, 6, 30), 500.0),
            (date(2025, 12, 31), 100.0),
            (date(2027, 3, 31), 700.0),
        )
        self.assertEqual(milestones.mapped("is_out_of_period"), [False, True, True])
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 6, 30)), 500.0
        )
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 12, 31)), 1200.0
        )

    def test_milestone_becomes_out_of_period_when_dates_change(self):
        po = self._make_po()
        milestone = self._create_milestones(po, (date(2026, 6, 30), 500.0))
        self.assertFalse(milestone.is_out_of_period)
        po.end_date = date(2026, 5, 31)
        self.assertTrue(milestone.is_out_of_period)

    def test_milestones_only_for_daily_method(self):
        po = self._make_po()
        self._create_milestones(po, (date(2026, 6, 30), 500.0))
        self.assertTrue(po._get_effective_milestones())
        po.recognition_at_date_method = False
        self.assertFalse(po._get_effective_milestones())

    # =========================================================
    # Validation
    # =========================================================

    def test_invalid_amounts(self):
        po = self._make_po()
        with self.assertRaisesRegex(ValidationError, r"cumulative"):
            self._create_milestones(po, (date(2026, 6, 30), 1300.0))
        with self.assertRaisesRegex(ValidationError, r"cumulative"):
            self._create_milestones(po, (date(2026, 6, 30), -1.0))

    def test_invalid_amount_ignored_when_out_of_period(self):
        po = self._make_po()
        self._create_milestones(po, (date(2027, 6, 30), 5000.0))

    # =========================================================
    # Wizard suggestion
    # =========================================================

    def test_wizard_suggested_amount_follows_milestones(self):
        po = self._make_po()
        self._create_milestones(po, (date(2026, 6, 30), 500.0))
        wizard = self._create_wizard(po, date="2026-06-30", description="Test")
        self.assertEqual(wizard.amount_to_recognize, 500.0)

    # =========================================================
    # Schedule generation
    # =========================================================

    def test_schedule_includes_milestone_dates(self):
        """A milestone date gets its own entry and its amount is reached
        exactly on that date."""
        po = self._make_po(
            total_amount=900.0,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self._create_milestones(
            po, (date(2026, 1, 15), 300.0), (date(2026, 2, 15), 600.0)
        )
        po._process_pending_regenerations()
        drafts = po._get_draft_schedule_moves()
        self.assertEqual(
            sorted(drafts.mapped("date")),
            [
                date(2026, 1, 15),
                date(2026, 1, 31),
                date(2026, 2, 15),
                date(2026, 2, 28),
                date(2026, 3, 31),
            ],
        )
        self.assertAlmostEqual(self._recognized_at(po, date(2026, 1, 15)), 300.0)
        self.assertAlmostEqual(self._recognized_at(po, date(2026, 2, 15)), 600.0)
        self.assertAlmostEqual(self._recognized_at(po, date(2026, 3, 31)), 900.0)

    def test_schedule_month_end_milestone_is_not_duplicated(self):
        po = self._make_po(
            total_amount=900.0,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self._create_milestones(po, (date(2026, 1, 31), 300.0))
        po._process_pending_regenerations()
        drafts = po._get_draft_schedule_moves()
        self.assertEqual(
            sorted(drafts.mapped("date")),
            [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)],
        )

    def test_schedule_keeps_posted_milestone_entry(self):
        """A milestone already covered by a posted entry is not regenerated,
        later milestones still are."""
        po = self._make_po(
            total_amount=900.0,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self._create_milestones(
            po, (date(2026, 1, 15), 300.0), (date(2026, 2, 15), 600.0)
        )
        po._process_pending_regenerations()
        first_draft = po._get_draft_schedule_moves().filtered(
            lambda m: m.date == date(2026, 1, 15)
        )
        self.assertTrue(first_draft)
        with self._mock_today(date(2026, 1, 15)):
            first_draft.action_post()
        self.assertEqual(first_draft.state, "posted")

        po.schedule_needs_regeneration = True
        po._process_pending_regenerations()

        self.assertEqual(first_draft.state, "posted")
        self.assertEqual(
            sorted(po._get_draft_schedule_moves().mapped("date")),
            [
                date(2026, 1, 31),
                date(2026, 2, 15),
                date(2026, 2, 28),
                date(2026, 3, 31),
            ],
        )
        self.assertAlmostEqual(self._recognized_at(po, date(2026, 1, 15)), 300.0)
        self.assertAlmostEqual(self._recognized_at(po, date(2026, 2, 15)), 600.0)
        self.assertAlmostEqual(self._recognized_at(po, date(2026, 3, 31)), 900.0)

    # =========================================================
    # Regeneration flag / locking
    # =========================================================

    def test_milestone_change_flags_schedule_regeneration(self):
        po = self._make_po()
        po.schedule_needs_regeneration = False
        milestone = self._create_milestones(po, (date(2026, 6, 30), 500.0))
        self.assertTrue(po.schedule_needs_regeneration)
        po.schedule_needs_regeneration = False
        milestone.amount = 600.0
        self.assertTrue(po.schedule_needs_regeneration)
        po.schedule_needs_regeneration = False
        milestone.unlink()
        self.assertTrue(po.schedule_needs_regeneration)

    def test_done_obligation_locks_milestones(self):
        po = self._make_po()
        milestone = self._create_milestones(po, (date(2026, 6, 30), 500.0))
        po.write({"state": "done"})
        with self.assertRaises(UserError):
            milestone.amount = 600.0
        with self.assertRaises(UserError):
            milestone.unlink()
        with self.assertRaises(UserError):
            self._create_milestones(po, (date(2026, 11, 30), 1000.0))
