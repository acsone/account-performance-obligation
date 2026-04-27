# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.exceptions import ValidationError

from odoo.addons.account_perf_obligation.tests.common import PerfObligationCommon


class TestStartEndDates(PerfObligationCommon):
    def _create_obligation(
        self,
        perf_type="income",
        total_amount=1000.0,
        recognition_at_date_method=None,
        start_date=None,
        end_date=None,
    ):
        vals = {
            "perf_type": perf_type,
            "total_amount": total_amount,
            "company_id": self.company.id,
        }
        if recognition_at_date_method:
            vals["recognition_at_date_method"] = recognition_at_date_method
        if start_date:
            vals["start_date"] = start_date
        if end_date:
            vals["end_date"] = end_date
        return self.env["perf.obligation"].create(vals)

    # =========================================================
    # Constraints
    # =========================================================

    def test_start_after_end_raises(self):
        """Start date after end date raises ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_obligation(
                recognition_at_date_method="daily",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 1, 1),
            )

    def test_method_without_dates_raises(self):
        """Daily method without dates raises ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_obligation(
                recognition_at_date_method="daily",
            )

    def test_method_with_only_start_raises(self):
        """Daily method with only start date raises."""
        with self.assertRaises(ValidationError):
            self._create_obligation(
                recognition_at_date_method="daily",
                start_date=date(2026, 1, 1),
            )

    def test_same_start_end_ok(self):
        """Start date equal to end date is valid (1 day)."""
        po = self._create_obligation(
            total_amount=100.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 15),
        )
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 3, 15)),
            100.0,
        )

    def test_dates_without_method_ok(self):
        """Dates without recognition method is allowed (manual mode)."""
        po = self._create_obligation(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.assertFalse(po.recognition_at_date_method)

    # =========================================================
    # Daily pro-rata computation
    # =========================================================

    def test_before_start_returns_zero(self):
        """Date before start returns 0."""
        po = self._create_obligation(
            total_amount=365.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2025, 12, 31)),
            0.0,
        )

    def test_at_end_returns_total(self):
        """Date at end returns total amount."""
        po = self._create_obligation(
            total_amount=365.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.assertAlmostEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 12, 31)),
            365.0,
        )

    def test_after_end_returns_total(self):
        """Date after end returns total amount."""
        po = self._create_obligation(
            total_amount=365.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.assertAlmostEqual(
            po._compute_amount_to_recognize_at_date(date(2027, 6, 15)),
            365.0,
        )

    def test_daily_prorate_simple(self):
        """Simple case: 365 over 365 days = 1.00/day."""
        po = self._create_obligation(
            total_amount=365.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        self.assertAlmostEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 1, 1)),
            1.0,
        )
        self.assertAlmostEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 1, 31)),
            31.0,
        )

    def test_daily_prorate_rounding(self):
        """Test rounding: 1000 over 3 days.

        daily = 1000/3 = 333.333...
        day 1: round(333.333...) = 333.33
        day 2: round(666.666...) = 666.67
        day 3: total = 1000.00 (exact)
        """
        po = self._create_obligation(
            total_amount=1000.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 1, 1)),
            333.33,
        )
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 1, 2)),
            666.67,
        )
        self.assertEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 1, 3)),
            1000.0,
        )

    def test_daily_prorate_total_equals_total_amount(self):
        """The last day always returns exactly total_amount."""
        po = self._create_obligation(
            total_amount=1000.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        result = po._compute_amount_to_recognize_at_date(date(2026, 12, 31))
        self.assertEqual(result, 1000.0)

    def test_daily_prorate_expense(self):
        """Daily pro-rata works the same for expenses."""
        po = self._create_obligation(
            perf_type="expense",
            total_amount=300.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        total_days = (date(2026, 3, 31) - date(2026, 1, 1)).days + 1  # 90
        daily = 300.0 / total_days
        expected = round(daily * 31, 2)
        self.assertAlmostEqual(
            po._compute_amount_to_recognize_at_date(date(2026, 1, 31)),
            expected,
        )

    # =========================================================
    # Wizard suggestion
    # =========================================================

    def test_wizard_suggested_amount(self):
        """Wizard pre-fills amount_to_recognize from obligation dates."""
        po = self._create_obligation(
            total_amount=1000.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 3),
        )
        wizard = self._create_wizard(po, date="2026-01-02", description="Test")
        self.assertAlmostEqual(wizard.amount_to_recognize, 666.67)

    def test_wizard_suggested_amount_no_method(self):
        """Without recognition method, amount_to_recognize is not auto-filled."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_recognition_at_date())
        wizard = self._create_wizard(
            po, amount=0, date="2026-01-15", description="Test"
        )
        self.assertEqual(wizard.amount_to_recognize, 0.0)

    # =========================================================
    # Integration: wizard with recognition
    # =========================================================

    def test_wizard_with_daily_recognition_income(self):
        """Full integration: invoice + daily pro-rata recognition."""
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
        suggested = po._compute_amount_to_recognize_at_date(date(2026, 1, 31))
        wizard = self._create_wizard(
            po,
            amount=suggested,
            date="2026-01-31",
            description="Jan reco",
        )
        result = wizard.action_confirm()
        move = self.env["account.move"].browse(result["res_id"])
        self.assertTrue(move)
        self.assertEqual(str(move.date), "2026-01-31")

    def test_wizard_with_daily_recognition_expense(self):
        """Full integration: bill + daily pro-rata recognition for expense."""
        po = self._create_obligation(
            perf_type="expense",
            total_amount=900.0,
            recognition_at_date_method="daily",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
        )
        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 900, False),
                (self.expense_account, 900, 0, po),
            ],
            date="2026-01-01",
        )
        suggested = po._compute_amount_to_recognize_at_date(date(2026, 1, 31))
        wizard = self._create_wizard(
            po,
            amount=suggested,
            date="2026-01-31",
            description="Jan reco",
        )
        result = wizard.action_confirm()
        move = self.env["account.move"].browse(result["res_id"])
        self.assertTrue(move)
        self.assertEqual(str(move.date), "2026-01-31")
