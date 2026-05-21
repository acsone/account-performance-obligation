# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError

from .common import PerfObligationCommon


class TestWizard(PerfObligationCommon):
    # =========================================================
    # UserError: no adjustment needed (wizard-only concern)
    # =========================================================

    def test_no_adjustment_needed_raises(self):
        """When _recognize returns None, the wizard raises UserError."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        wizard = self._create_wizard(po, 1000)
        with self.assertRaisesRegex(UserError, r"No adjustment is needed"):
            wizard.action_confirm()

    def test_recognize_same_amount_twice_raises(self):
        """Recognizing the same cumulative amount again raises UserError."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_wizard(
            po, 500, date="2026-01-31", description="Jan"
        ).action_confirm()
        w2 = self._create_wizard(po, 500, date="2026-02-28", description="Feb")
        with self.assertRaisesRegex(UserError, r"No adjustment is needed"):
            w2.action_confirm()

    # =========================================================
    # Move metadata produced by the wizard
    # =========================================================

    def test_move_metadata_and_labels(self):
        """action_confirm produces a move with the correct metadata."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        result = self._create_wizard(
            po, 500, date="2025-02-28", description="Feb reco"
        ).action_confirm()
        move = self.env["account.move"].browse(result["res_id"])

        self.assertEqual(str(move.date), "2025-02-28")
        self.assertEqual(move.ref, f"{po.name} - Feb reco")
        self.assertEqual(move.journal_id, self.reco_journal)
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.auto_post, "monthly")

        for line in move.line_ids:
            self.assertEqual(line.name, "Feb reco")
            self.assertEqual(line.perf_obligation_id, po)

    def test_action_confirm_returns_act_window_with_res_id(self):
        """action_confirm returns an act_window pointing to the created move."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        result = self._create_wizard(po, 200, date="2026-01-31").action_confirm()
        self.assertIn("res_id", result)
        self.assertEqual(result["res_model"], "account.move")
        move = self.env["account.move"].browse(result["res_id"])
        self.assertTrue(move.exists())
