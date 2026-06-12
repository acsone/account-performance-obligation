# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from odoo import fields
from odoo.exceptions import ValidationError

from .common import PerfObligationObsCommon


class TestObsConfig(PerfObligationObsCommon):
    """Test configuration validation (_get_obs_config)."""

    def test_get_obs_config_returns_all_fields(self):
        """_get_obs_config returns journal, commitment_account and
        counterpart_account."""
        po = self._create_obligation()
        config = po._get_obs_config()
        self.assertEqual(config["journal"], self.obs_journal)
        self.assertEqual(config["commitment_account"], self.obs_income_account)
        self.assertEqual(config["counterpart_account"], self.obs_counterpart_account)

    def test_missing_obs_journal_raises(self):
        """Missing OBS journal raises ValidationError on config retrieval."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self.company.po_obs_journal_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._get_obs_config()

    def test_missing_obs_debit_account_raises(self):
        """Missing OBS income account raises ValidationError."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self.company.po_obs_income_account_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._get_obs_config()

    def test_missing_obs_credit_account_raises(self):
        """Missing OBS counterpart account raises ValidationError."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self.company.po_obs_counterpart_account_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._get_obs_config()


class TestObsInitialMove(PerfObligationObsCommon):
    """Test the initial OBS journal entry created on obligation creation."""

    def test_initial_move_created_on_obligation_creation(self):
        """Creating an obligation automatically creates an OBS entry."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        self.assertTrue(obs_lines, "Expected OBS move lines to exist after creation.")

    def test_initial_move_has_two_lines(self):
        """The initial OBS entry has exactly two lines linked to the obligation."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        self.assertEqual(len(obs_lines), 2)

    def test_initial_move_debit_line(self):
        """The initial OBS debit line uses the OBS income account for total_amount."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        debit_line = obs_lines.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        self.assertEqual(len(debit_line), 1)
        self.assertAlmostEqual(debit_line.debit, 1000)
        self.assertAlmostEqual(debit_line.credit, 0)

    def test_initial_move_credit_line(self):
        """The initial OBS credit line uses the OBS counterpart account for
        total_amount."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        credit_line = obs_lines.filtered(
            lambda line: line.account_id == self.obs_counterpart_account
        )
        self.assertEqual(len(credit_line), 1)
        self.assertAlmostEqual(credit_line.credit, 1000)
        self.assertAlmostEqual(credit_line.debit, 0)

    def test_initial_move_is_posted(self):
        """The initial OBS journal entry is posted immediately."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        self.assertTrue(
            all(line.parent_state == "posted" for line in obs_lines),
            "All OBS lines should belong to a posted move.",
        )

    def test_initial_move_ref_is_obligation_name(self):
        """The initial OBS entry's ref equals the obligation's reference."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        move = obs_lines.mapped("move_id")
        self.assertEqual(len(move), 1)
        self.assertEqual(move.ref, po.name)

    def test_initial_move_journal_is_obs_journal(self):
        """The initial OBS entry is posted in the OBS journal."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        move = obs_lines.mapped("move_id")
        self.assertEqual(move.journal_id, self.obs_journal)

    def test_initial_move_both_lines_linked_to_obligation(self):
        """Both lines in the initial OBS entry carry the obligation's id."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        self.assertTrue(
            all(line.perf_obligation_id == po for line in obs_lines),
            "Every OBS line must be linked to the obligation.",
        )

    def test_initial_move_expense_obligation(self):
        """The initial OBS entry is also created for expense obligations."""
        po = self._create_obligation(perf_type="expense", total_amount=500)
        obs_lines = self._get_obs_lines(po)
        self.assertEqual(len(obs_lines), 2)
        debit_line = obs_lines.filtered(
            lambda line: line.account_id == self.obs_expense_account
        )
        credit_line = obs_lines.filtered(
            lambda line: line.account_id == self.obs_counterpart_account
        )
        self.assertAlmostEqual(debit_line.debit, 500)
        self.assertAlmostEqual(credit_line.credit, 500)

    def test_missing_obs_config_skips_obs_entry_on_creation(self):
        """If OBS config is incomplete, obligation creation succeeds but no OBS
        entry is created."""
        self.company.po_obs_journal_id = False
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.assertTrue(po.exists())
        obs_lines = self._get_obs_lines(po)
        self.assertFalse(
            obs_lines, "No OBS lines should be created when config is missing."
        )

    def test_initial_move_date_is_today(self):
        """The initial OBS entry is dated today."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_lines = self._get_obs_lines(po)
        move = obs_lines.mapped("move_id")
        self.assertEqual(
            move.date, fields.Date.context_today(self.env["perf.obligation"])
        )


class TestObsBalanceHelpers(PerfObligationObsCommon):
    """Unit tests for the balance-query helper."""

    def test_obs_debit_balance_equals_total_amount_after_creation(self):
        """After creation, the OBS commitment balance equals total_amount."""
        po = self._create_obligation(perf_type="income", total_amount=1200)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 1200)

    def test_obs_debit_balance_zero_for_fresh_obligation_without_config(self):
        """_get_obs_commitment_account_balance returns 0 when no lines match
        (simulated by pointing the income account to a different account)."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        original = self.company.po_obs_income_account_id
        other_account = self.env["account.account"].create(
            {
                "name": "Other OBS income",
                "code": "8IOBT2",
                "account_type": "off_balance",
            }
        )
        self.company.po_obs_income_account_id = other_account
        self.assertAlmostEqual(self._obs_commitment_balance(po), 0.0)
        self.company.po_obs_income_account_id = original


class TestObsAdjustment(PerfObligationObsCommon):
    """Test the _adjust_obs method: no adjustment, A>B and A<B cases."""

    def test_no_adjustment_when_a_equals_b(self):
        """_adjust_obs returns None when A == B (no recognition yet)."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        result = po._adjust_obs()
        self.assertIsNone(result)

    def test_no_adjustment_after_full_recognition(self):
        """_adjust_obs returns None when obligation is fully recognized
        and A has been reduced to match B == 0."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self._create_and_post_move(
            self.obs_journal,
            [
                (self.obs_counterpart_account, 500, 0, po),
                (self.obs_income_account, 0, 500, po),
            ],
            date="2026-01-31",
        )
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 500, 0, po),
                (self.inc_pl, 0, 500, po),
            ],
            date="2026-01-31",
        )
        result = po._adjust_obs()
        self.assertIsNone(result)

    def test_adjustment_a_greater_than_b_income(self):
        """When A > B (some income recognized), _adjust_obs creates a
        decreasing entry: credit commitment account, debit counterpart account."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 400, 0, po),
                (self.inc_pl, 0, 400, po),
            ],
            date="2026-01-31",
        )

        move = po._adjust_obs()

        self.assertIsNotNone(move, "An adjustment entry should have been created.")
        self.assertEqual(move.journal_id, self.obs_journal)
        self.assertEqual(move.state, "posted")

        lines = move.line_ids
        self.assertEqual(len(lines), 2)

        credit_side = lines.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        self.assertEqual(len(credit_side), 1)
        self.assertAlmostEqual(credit_side.credit, 400)
        self.assertAlmostEqual(credit_side.debit, 0)

        debit_side = lines.filtered(
            lambda line: line.account_id == self.obs_counterpart_account
        )
        self.assertEqual(len(debit_side), 1)
        self.assertAlmostEqual(debit_side.debit, 400)
        self.assertAlmostEqual(debit_side.credit, 0)

    def test_adjustment_a_greater_than_b_expense(self):
        """Same A > B logic applies to expense obligations."""
        po = self._create_obligation(perf_type="expense", total_amount=800)
        self._create_and_post_move(
            self.exp_reco_journal,
            [
                (self.exp_pl, 200, 0, po),
                (self.exp_credit_bs, 0, 200, po),
            ],
            date="2026-01-31",
        )

        move = po._adjust_obs()

        self.assertIsNotNone(move)
        lines = move.line_ids
        credit_side = lines.filtered(
            lambda line: line.account_id == self.obs_expense_account
        )
        debit_side = lines.filtered(
            lambda line: line.account_id == self.obs_counterpart_account
        )
        self.assertAlmostEqual(credit_side.credit, 200)
        self.assertAlmostEqual(debit_side.debit, 200)

    def test_adjustment_amount_a_greater_than_b(self):
        """The adjustment amount equals A - B exactly."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 250, 0, po),
                (self.inc_pl, 0, 250, po),
            ],
            date="2026-01-31",
        )
        move = po._adjust_obs()
        credit_side = move.line_ids.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        self.assertAlmostEqual(credit_side.credit, 250)

    def test_adjustment_a_less_than_b(self):
        """When A < B, _adjust_obs creates an increasing entry:
        debit commitment account, credit counterpart account."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.obs_journal,
            [
                (self.obs_counterpart_account, 300, 0, po),
                (self.obs_income_account, 0, 300, po),
            ],
            date="2026-01-31",
        )

        move = po._adjust_obs()

        self.assertIsNotNone(move)
        lines = move.line_ids
        self.assertEqual(len(lines), 2)

        debit_side = lines.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        credit_side = lines.filtered(
            lambda line: line.account_id == self.obs_counterpart_account
        )
        self.assertAlmostEqual(debit_side.debit, 300)
        self.assertAlmostEqual(credit_side.credit, 300)

    def test_adjustment_move_is_posted(self):
        """The adjustment entry is posted immediately."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 100, 0, po), (self.inc_pl, 0, 100, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs()
        self.assertEqual(move.state, "posted")

    def test_adjustment_move_ref_is_obligation_name(self):
        """The adjustment entry's ref equals the obligation's reference."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 100, 0, po), (self.inc_pl, 0, 100, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs()
        self.assertEqual(move.ref, po.name)

    def test_adjustment_lines_linked_to_obligation(self):
        """Both lines in the adjustment entry are linked to the obligation."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 100, 0, po), (self.inc_pl, 0, 100, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs()
        self.assertTrue(
            all(line.perf_obligation_id == po for line in move.line_ids),
            "All adjustment lines must be linked to the obligation.",
        )

    def test_adjustment_after_adjust_returns_none(self):
        """Running _adjust_obs a second time with no further change returns None."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-01-31",
        )
        po._adjust_obs()
        result = po._adjust_obs()
        self.assertIsNone(result)

    def test_missing_obs_config_raises_in_adjust(self):
        """_adjust_obs raises ValidationError when OBS config is missing."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.company.po_obs_journal_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._adjust_obs()


class TestObsWizard(PerfObligationObsCommon):
    """Test the manual adjustment wizard."""

    def test_wizard_adjusts_at_given_date(self):
        """Wizard creates adjustment entries at the chosen date."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 400, 0, po), (self.inc_pl, 0, 400, po)],
            date="2026-01-31",
        )
        obs_before = len(self._get_obs_lines(po))
        wizard = self.env["perf.obligation.obs.adjust.wizard"].create(
            {"date": "2026-01-31"}
        )
        wizard.action_adjust()
        self.assertGreater(len(self._get_obs_lines(po)), obs_before)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 600)

    def test_wizard_adjustment_dated_at_wizard_date(self):
        """The adjustment entry is dated at the date chosen in the wizard."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 200, 0, po), (self.inc_pl, 0, 200, po)],
            date="2026-03-31",
        )
        wizard = self.env["perf.obligation.obs.adjust.wizard"].create(
            {"date": "2026-03-31"}
        )
        wizard.action_adjust()
        obs_lines = self._get_obs_lines(po)
        adjustment_moves = obs_lines.mapped("move_id").filtered(
            lambda m: m.date == datetime.date(2026, 3, 31)
            and any(
                line.credit > 0 and line.account_id == self.obs_income_account
                for line in m.line_ids
            )
        )
        self.assertTrue(adjustment_moves)

    def test_wizard_no_adjustment_when_balanced(self):
        """Wizard does nothing when all obligations are already balanced."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        obs_before = len(self._get_obs_lines(po))
        wizard = self.env["perf.obligation.obs.adjust.wizard"].create(
            {"date": "2026-01-31"}
        )
        wizard.action_adjust()
        self.assertEqual(len(self._get_obs_lines(po)), obs_before)


class TestObsEndToEnd(PerfObligationObsCommon):
    """End-to-end scenario tests: obligation lifecycle with OBS tracking."""

    def test_income_obligation_full_lifecycle(self):
        """Full income lifecycle: creation → partial recognition → full recognition."""
        po = self._create_obligation(perf_type="income", total_amount=900)

        self.assertAlmostEqual(self._obs_commitment_balance(po), 900)
        self.assertIsNone(po._adjust_obs())

        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-01-31",
        )
        move1 = po._adjust_obs()
        self.assertIsNotNone(move1)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 600)
        self.assertIsNone(po._adjust_obs())

        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-02-28",
        )
        move2 = po._adjust_obs()
        self.assertIsNotNone(move2)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 300)
        self.assertIsNone(po._adjust_obs())

        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-03-31",
        )
        move3 = po._adjust_obs()
        self.assertIsNotNone(move3)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 0)
        self.assertIsNone(po._adjust_obs())

    def test_expense_obligation_full_lifecycle(self):
        """Full expense lifecycle mirrors income, using expense P&L accounts."""
        po = self._create_obligation(perf_type="expense", total_amount=600)

        self.assertAlmostEqual(self._obs_commitment_balance(po), 600)
        self.assertIsNone(po._adjust_obs())

        self._create_and_post_move(
            self.exp_reco_journal,
            [(self.exp_pl, 200, 0, po), (self.exp_credit_bs, 0, 200, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs()
        self.assertIsNotNone(move)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 400)
        self.assertIsNone(po._adjust_obs())

    def test_obs_debit_balance_after_two_adjustments(self):
        """Two successive partial recognitions produce two adjustments and
        the commitment balance tracks correctly at each step."""
        po = self._create_obligation(perf_type="income", total_amount=1200)

        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 400, 0, po), (self.inc_pl, 0, 400, po)],
            date="2026-01-31",
        )
        po._adjust_obs()
        self.assertAlmostEqual(self._obs_commitment_balance(po), 800)

        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 400, 0, po), (self.inc_pl, 0, 400, po)],
            date="2026-02-28",
        )
        po._adjust_obs()
        self.assertAlmostEqual(self._obs_commitment_balance(po), 400)
