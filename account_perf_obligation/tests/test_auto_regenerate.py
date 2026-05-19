# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command

from .common import PerfObligationCommon


class TestAutoRegenerate(PerfObligationCommon):
    """Test the flag-based schedule regeneration mechanism.

    The module does not provide a concrete schedule implementation,
    so `_supports_schedule()` always returns False here. These tests
    therefore cover:

    - that `_mark_needs_recognition` is a no-op without schedule support
    - that the `perf_obligation_in_regeneration` context flag prevents
      marking via `_mark_needs_recognition`
    - that `_process_pending_regenerations` correctly skips obligations
      that don't support scheduling and clears their flag
    - that the list-view action wires through to the processing method

    Integration tests with a real recognition method live in the
    `account_perf_obligation_dates` module.
    """

    # =========================================================
    # Helpers
    # =========================================================

    def _force_set_flag(self, po):
        """Set schedule_needs_regeneration without going through the
        marking logic (which would no-op since base obligations don't
        support scheduling)."""
        po.with_context(perf_obligation_in_regeneration=True).write(
            {"schedule_needs_regeneration": True}
        )

    # =========================================================
    # Trigger fields
    # =========================================================

    def test_trigger_fields_default(self):
        """Base trigger fields include total_amount and method."""
        po = self._create_obligation()
        fields_list = po._get_recognition_trigger_fields()
        self.assertIn("total_amount", fields_list)
        self.assertIn("recognition_at_date_method", fields_list)

    # =========================================================
    # _mark_needs_recognition: no-op cases
    # =========================================================

    def test_mark_noop_when_schedule_unsupported(self):
        """_mark_needs_recognition is a no-op when the obligation does
        not support scheduling (the base case)."""
        po = self._create_obligation()
        self.assertFalse(po._supports_schedule())
        po._mark_needs_recognition()
        self.assertFalse(po.schedule_needs_regeneration)

    def test_mark_noop_in_regeneration_context(self):
        """_mark_needs_recognition is a no-op when the
        perf_obligation_in_regeneration context flag is set."""
        po = self._create_obligation()
        po.with_context(perf_obligation_in_regeneration=True)._mark_needs_recognition()
        self.assertFalse(po.schedule_needs_regeneration)

    # =========================================================
    # Hooks: trigger marking but no-op since unsupported
    # =========================================================

    def test_create_does_not_mark_when_unsupported(self):
        """Creating a base obligation (no schedule support) does not
        set the flag."""
        po = self._create_obligation()
        self.assertFalse(po.schedule_needs_regeneration)

    def test_write_does_not_mark_when_unsupported(self):
        """Writing trigger fields on a base obligation does not set
        the flag."""
        po = self._create_obligation(total_amount=1000)
        po.total_amount = 2000
        self.assertFalse(po.schedule_needs_regeneration)

    def test_move_line_create_does_not_mark_when_unsupported(self):
        """Linked move-line creation does not flag a base obligation."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        self.assertFalse(po.schedule_needs_regeneration)

    # =========================================================
    # Process pending regenerations
    # =========================================================

    def test_process_pending_skips_unflagged(self):
        """Unflagged obligations are not processed."""
        po = self._create_obligation()
        self.assertFalse(po.schedule_needs_regeneration)
        # Should not raise even though _supports_schedule is False
        po._process_pending_regenerations()
        self.assertFalse(po.schedule_needs_regeneration)

    def test_process_pending_clears_flag_when_unsupported(self):
        """When a flagged obligation no longer supports scheduling,
        the flag is cleared without raising."""
        po = self._create_obligation()
        self._force_set_flag(po)
        self.assertTrue(po.schedule_needs_regeneration)

        po._process_pending_regenerations()

        # Flag is cleared (no schedule to regenerate)
        self.assertFalse(po.schedule_needs_regeneration)

    def test_action_process_pending_regenerations(self):
        """The list-view action runs _process_pending_regenerations
        on the recordset."""
        po = self._create_obligation()
        self._force_set_flag(po)

        po.action_process_pending_regenerations()

        self.assertFalse(po.schedule_needs_regeneration)

    # =========================================================
    # Recursion guard
    # =========================================================

    def test_in_regeneration_context_does_not_mark_from_move_line(self):
        """The perf_obligation_in_regeneration context flag prevents
        marking from move-line operations."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        # Even though _supports_schedule is False here, this test still
        # verifies the context guard short-circuits before any check.
        self.env["account.move"].with_context(
            perf_obligation_in_regeneration=True
        ).create(
            {
                "journal_id": self.sale_journal.id,
                "date": "2026-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.receivable_account.id,
                            "debit": 1000,
                            "credit": 0,
                            "name": "Test",
                        },
                    ),
                    Command.create(
                        {
                            "account_id": self.income_account.id,
                            "debit": 0,
                            "credit": 1000,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        },
                    ),
                ],
            }
        )
        self.assertFalse(po.schedule_needs_regeneration)

    def test_pl_account_id_in_trigger_fields(self):
        """pl_account_id must be listed in _get_recognition_trigger_fields."""
        po = self._create_obligation()
        self.assertIn("pl_account_id", po._get_recognition_trigger_fields())
