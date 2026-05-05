# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo.exceptions import ValidationError

from odoo.addons.account_perf_obligation.tests.common import PerfObligationCommon


class TestRecognitionCap(PerfObligationCommon):
    """Tests for the recognition cap feature."""

    def _make_po(self, perf_type="income", total_amount=1200.0):
        return self._create_obligation(perf_type=perf_type, total_amount=total_amount)

    def _set_cap(self, po, enabled, amount=0.0):
        """Enable or disable the cap directly via write on the obligation."""
        po.write(
            {
                "recognition_cap_enabled": enabled,
                "recognition_cap_amount": amount if enabled else 0.0,
            }
        )
        po.invalidate_recordset()

    def _clear_flag(self, po):
        po.with_context(perf_obligation_in_regeneration=True).write(
            {"schedule_needs_regeneration": False}
        )

    def test_cap_cannot_be_negative_on_positive_obligation(self):
        """A negative cap on a positive obligation violates sign rule."""
        po = self._make_po(total_amount=1000.0)
        with self.assertRaisesRegex(ValidationError, r"same sign"):
            self._set_cap(po, enabled=True, amount=-10.0)

    def test_cap_cannot_exceed_total_positive(self):
        po = self._make_po(total_amount=1000.0)
        with self.assertRaisesRegex(ValidationError, r"cannot exceed"):
            self._set_cap(po, enabled=True, amount=1500.0)

    def test_cap_equal_to_total_positive_allowed(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=1000.0)
        self.assertTrue(po.recognition_cap_enabled)
        self.assertAlmostEqual(po.recognition_cap_amount, 1000.0)

    def test_cap_zero_allowed_on_positive_obligation(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=0.0)
        self.assertTrue(po.recognition_cap_enabled)
        self.assertAlmostEqual(po.recognition_cap_amount, 0.0)

    def test_cap_cannot_be_positive_on_negative_obligation(self):
        """A positive cap on a negative obligation violates sign rule."""
        po = self._make_po(total_amount=-1000.0)
        with self.assertRaisesRegex(ValidationError, r"same sign"):
            self._set_cap(po, enabled=True, amount=10.0)

    def test_cap_cannot_exceed_total_negative(self):
        """abs(cap) > abs(total) is rejected for negative obligations."""
        po = self._make_po(total_amount=-1000.0)
        with self.assertRaisesRegex(ValidationError, r"cannot exceed"):
            self._set_cap(po, enabled=True, amount=-1500.0)

    def test_cap_equal_to_total_negative_allowed(self):
        po = self._make_po(total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=-1000.0)
        self.assertTrue(po.recognition_cap_enabled)
        self.assertAlmostEqual(po.recognition_cap_amount, -1000.0)

    def test_cap_zero_allowed_on_negative_obligation(self):
        po = self._make_po(total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=0.0)
        self.assertTrue(po.recognition_cap_enabled)
        self.assertAlmostEqual(po.recognition_cap_amount, 0.0)

    def test_set_cap_enables_flag_and_amount(self):
        po = self._make_po()
        self._set_cap(po, enabled=True, amount=400.0)
        self.assertTrue(po.recognition_cap_enabled)
        self.assertAlmostEqual(po.recognition_cap_amount, 400.0)

    def test_set_cap_disable_clears_amount(self):
        po = self._make_po()
        self._set_cap(po, enabled=True, amount=400.0)
        self._set_cap(po, enabled=False)
        self.assertFalse(po.recognition_cap_enabled)
        self.assertAlmostEqual(po.recognition_cap_amount, 0.0)

    def test_set_cap_triggers_regeneration_when_schedule_supported(self):
        po = self._make_po()
        self._clear_flag(po)
        with patch.object(type(po), "_supports_schedule", return_value=True):
            self._set_cap(po, enabled=True, amount=400.0)
        self.assertTrue(po.schedule_needs_regeneration)

    def test_set_cap_no_flag_when_schedule_unsupported(self):
        po = self._make_po()
        self._clear_flag(po)
        # _supports_schedule returns False by default in the base module
        self._set_cap(po, enabled=True, amount=400.0)
        self.assertFalse(po.schedule_needs_regeneration)

    def test_apply_cap_disabled(self):
        po = self._make_po(total_amount=1000.0)
        self.assertFalse(po.recognition_cap_enabled)
        self.assertAlmostEqual(po._apply_recognition_cap(800.0), 800.0)

    def test_apply_cap_positive_amount_below_cap(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=400.0)
        self.assertAlmostEqual(po._apply_recognition_cap(300.0), 300.0)

    def test_apply_cap_positive_amount_above_cap(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=400.0)
        self.assertAlmostEqual(po._apply_recognition_cap(600.0), 400.0)

    def test_apply_cap_positive_amount_equals_cap(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=400.0)
        self.assertAlmostEqual(po._apply_recognition_cap(400.0), 400.0)

    def test_apply_cap_negative_amount_above_cap_in_abs(self):
        """For a negative obligation, -600 is 'more' than -400 in
        absolute terms and must be capped to -400."""
        po = self._make_po(total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=-400.0)
        self.assertAlmostEqual(po._apply_recognition_cap(-600.0), -400.0)

    def test_apply_cap_negative_amount_below_cap_in_abs(self):
        """For a negative obligation, -200 is 'less' than -400 in
        absolute terms and must pass through unchanged."""
        po = self._make_po(total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=-400.0)
        self.assertAlmostEqual(po._apply_recognition_cap(-200.0), -200.0)

    def test_apply_cap_negative_amount_equals_cap(self):
        po = self._make_po(total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=-400.0)
        self.assertAlmostEqual(po._apply_recognition_cap(-400.0), -400.0)

    def test_trigger_fields_includes_cap_fields(self):
        po = self._make_po()
        trigger_fields = po._get_recognition_trigger_fields()
        self.assertIn("recognition_cap_enabled", trigger_fields)
        self.assertIn("recognition_cap_amount", trigger_fields)

    def test_manual_wizard_above_cap_raises(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=400.0)
        wizard = self._create_wizard(
            po, amount=500.0, date="2026-04-30", description="Test"
        )
        with self.assertRaisesRegex(
            ValidationError, r"cannot exceed the recognition cap"
        ):
            wizard.action_confirm()

    def test_manual_wizard_at_cap_succeeds(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=400.0)
        wizard = self._create_wizard(
            po, amount=400.0, date="2026-04-30", description="Test"
        )
        result = wizard.action_confirm()
        self.assertTrue(result)

    def test_manual_wizard_below_cap_succeeds(self):
        po = self._make_po(total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=400.0)
        wizard = self._create_wizard(
            po, amount=200.0, date="2026-02-28", description="Test"
        )
        result = wizard.action_confirm()
        self.assertTrue(result)

    def test_manual_wizard_no_cap_no_restriction(self):
        po = self._make_po(total_amount=1000.0)
        self.assertFalse(po.recognition_cap_enabled)
        wizard = self._create_wizard(
            po, amount=1000.0, date="2026-12-31", description="Full"
        )
        result = wizard.action_confirm()
        self.assertTrue(result)

    def test_manual_wizard_negative_obligation_above_cap_raises(self):
        """For a negative obligation with cap -400, recognizing -500
        (abs > abs(cap)) must raise."""
        po = self._make_po(perf_type="expense", total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=-400.0)
        wizard = self._create_wizard(
            po, amount=-500.0, date="2026-04-30", description="Test"
        )
        with self.assertRaisesRegex(
            ValidationError, r"cannot exceed the recognition cap"
        ):
            wizard.action_confirm()

    def test_manual_wizard_negative_obligation_at_cap_succeeds(self):
        po = self._make_po(perf_type="expense", total_amount=-1000.0)
        self._set_cap(po, enabled=True, amount=-400.0)
        wizard = self._create_wizard(
            po, amount=-400.0, date="2026-04-30", description="Test"
        )
        result = wizard.action_confirm()
        self.assertTrue(result)

    def test_expense_manual_wizard_above_cap_raises(self):
        po = self._make_po(perf_type="expense", total_amount=1000.0)
        self._set_cap(po, enabled=True, amount=300.0)
        wizard = self._create_wizard(
            po, amount=400.0, date="2026-04-30", description="Test"
        )
        with self.assertRaisesRegex(
            ValidationError, r"cannot exceed the recognition cap"
        ):
            wizard.action_confirm()

    def test_cap_disabled_no_restriction(self):
        po = self._make_po(total_amount=1000.0)
        self.assertFalse(po.recognition_cap_enabled)
        wizard = self._create_wizard(
            po, amount=1000.0, date="2026-12-31", description="Full"
        )
        result = wizard.action_confirm()
        self.assertTrue(result)
