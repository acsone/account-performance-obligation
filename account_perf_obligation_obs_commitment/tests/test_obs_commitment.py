# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.exceptions import ValidationError

from .common import PerfObligationObsCommitmentCommon


class TestObsCommitmentConfig(PerfObligationObsCommitmentCommon):
    """Test configuration validation (_get_obs_commitment_config)."""

    def test_get_obs_commitment_config_returns_all_fields(self):
        """_get_obs_commitment_config returns journal, commitment_account and
        counterpart_account."""
        po = self._create_obligation()
        config = po._get_obs_commitment_config()
        self.assertEqual(config.journal, self.obs_journal)
        self.assertEqual(config.commitment_account, self.obs_income_account)
        self.assertEqual(config.counterpart_account, self.obs_counter_account)

    def test_missing_obs_journal_raises(self):
        """Missing OBS commitment journal raises ValidationError on config retrieval."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self.company.po_obs_commitment_journal_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._get_obs_commitment_config()

    def test_missing_obs_debit_account_raises(self):
        """Missing OBS commitment income account raises ValidationError."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self.company.po_obs_commitment_income_account_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._get_obs_commitment_config()

    def test_missing_obs_credit_account_raises(self):
        """Missing OBS commitment counterpart account raises ValidationError."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        self.company.po_obs_commitment_counterpart_account_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing off-balance sheet"):
            po._get_obs_commitment_config()


class TestObsCommitmentBalanceHelpers(PerfObligationObsCommitmentCommon):
    """Unit tests for the balance-query helper."""

    def test_obs_debit_balance_zero_for_fresh_obligation_without_config(self):
        """_get_obs_commitment_account_balance returns 0 when no lines match
        (simulated by pointing the income account to a different account)."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        original = self.company.po_obs_commitment_income_account_id
        other_account = self.env["account.account"].create(
            {
                "name": "Other OBS commitment income",
                "code": "8IOBT2",
                "account_type": "off_balance",
            }
        )
        self.company.po_obs_commitment_income_account_id = other_account
        self.assertAlmostEqual(self._obs_commitment_balance(po), 0.0)
        self.company.po_obs_commitment_income_account_id = original


class TestObsCommitmentAdjustment(PerfObligationObsCommitmentCommon):
    """Test the _adjust_obs_commitment method: no adjustment, A>B and A<B cases."""

    def test_no_adjustment_when_a_equals_b(self):
        """_adjust_obs_commitment returns None when A == B (already adjusted, no new
        recognition)."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        result = po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self.assertIsNone(result)

    def test_no_adjustment_after_full_recognition(self):
        """_adjust_obs_commitment returns None when obligation is fully recognized."""
        po = self._create_obligation(perf_type="income", total_amount=500)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 500, 0, po),
                (self.inc_pl, 0, 500, po),
            ],
            date="2026-01-31",
        )
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        result = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNone(result)

    def test_adjustment_a_greater_than_b_income(self):
        """When A > B (some income recognized), _adjust_obs_commitment creates a
        decreasing entry: credit commitment account, debit counterpart account."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 400, 0, po),
                (self.inc_pl, 0, 400, po),
            ],
            date="2026-01-31",
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNotNone(move, "An adjustment entry should have been created.")
        self.assertEqual(move.journal_id, self.obs_journal)
        self.assertEqual(move.state, "posted")
        lines = move.line_ids
        self.assertEqual(len(lines), 2)
        credit_side = lines.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        self.assertEqual(len(credit_side), 1)
        self.assertAlmostEqual(credit_side.debit, 400)
        self.assertAlmostEqual(credit_side.credit, 0)
        debit_side = lines.filtered(
            lambda line: line.account_id == self.obs_counter_account
        )
        self.assertEqual(len(debit_side), 1)
        self.assertAlmostEqual(debit_side.credit, 400)
        self.assertAlmostEqual(debit_side.debit, 0)

    def test_adjustment_a_greater_than_b_expense(self):
        """Same A > B logic applies to expense obligations."""
        po = self._create_obligation(perf_type="expense", total_amount=800)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self._create_and_post_move(
            self.exp_reco_journal,
            [
                (self.exp_pl, 200, 0, po),
                (self.exp_credit_bs, 0, 200, po),
            ],
            date="2026-01-31",
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNotNone(move)
        lines = move.line_ids
        credit_side = lines.filtered(
            lambda line: line.account_id == self.obs_expense_account
        )
        debit_side = lines.filtered(
            lambda line: line.account_id == self.obs_counter_account
        )
        self.assertAlmostEqual(credit_side.credit, 200)
        self.assertAlmostEqual(debit_side.debit, 200)

    def test_adjustment_amount_a_greater_than_b(self):
        """The adjustment amount equals A - B exactly."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self._create_and_post_move(
            self.reco_journal,
            [
                (self.inc_debit_bs, 250, 0, po),
                (self.inc_pl, 0, 250, po),
            ],
            date="2026-01-31",
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        credit_side = move.line_ids.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        self.assertAlmostEqual(credit_side.debit, 250)

    def test_adjustment_a_less_than_b(self):
        """When A < B, _adjust_obs_commitment creates an increasing entry:
        debit commitment account, credit counterpart account."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        # Simulate an out-of-band manual entry that decreased the commitment
        # balance by 300 outside of the adjustment engine.
        self._create_and_post_obs_move(
            self.obs_income_account, 0, 300, po, date="2026-01-31"
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNotNone(move)
        lines = move.line_ids
        self.assertEqual(len(lines), 2)
        debit_side = lines.filtered(
            lambda line: line.account_id == self.obs_income_account
        )
        credit_side = lines.filtered(
            lambda line: line.account_id == self.obs_counter_account
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
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertEqual(move.state, "posted")

    def test_adjustment_move_ref_is_obligation_name(self):
        """The adjustment entry's ref equals the obligation's reference."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 100, 0, po), (self.inc_pl, 0, 100, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertEqual(move.ref, po.name)

    def test_adjustment_lines_linked_to_obligation(self):
        """Only the commitment line in the adjustment entry is linked to the
        obligation, via `perf_obligation_id`. Neither line appears in the
        recognition schedule because off-balance sheet accounts are excluded
        from schedule views."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 100, 0, po), (self.inc_pl, 0, 100, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        linked_lines = move.line_ids.filtered(
            lambda line: line.perf_obligation_id == po
        )
        self.assertEqual(
            len(linked_lines),
            1,
            "Exactly the commitment line should be linked to the obligation.",
        )
        self.assertEqual(linked_lines.account_id, self.obs_income_account)

    def test_adjustment_after_adjust_returns_none(self):
        """Running _adjust_obs_commitment a second time with no further change
        returns None."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-01-31",
        )
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        result = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNone(result)

    def test_adjust_raises_when_draft_move_before_date(self):
        """Adjustment is blocked if a draft move linked to the obligation is
        dated on or before the adjustment date: the recognized amount can't
        be trusted while it's still unposted."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.env["account.move"].create(
            {
                "journal_id": self.reco_journal.id,
                "date": "2026-01-31",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.inc_debit_bs.id,
                            "debit": 300,
                            "credit": 0,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.inc_pl.id,
                            "debit": 0,
                            "credit": 300,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                ],
            }
        )
        with self.assertRaisesRegex(ValidationError, r"not posted yet"):
            po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))

    def test_adjust_not_blocked_by_draft_move_after_date(self):
        """A draft move dated after the adjustment date does not block it."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.env["account.move"].create(
            {
                "journal_id": self.reco_journal.id,
                "date": "2026-02-28",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.inc_debit_bs.id,
                            "debit": 300,
                            "credit": 0,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.inc_pl.id,
                            "debit": 0,
                            "credit": 300,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                ],
            }
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNotNone(move)

    def test_missing_obs_config_raises_in_adjust(self):
        """_adjust_obs_commitment raises ValidationError when OBS commitment config
        is missing."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.company.po_obs_commitment_journal_id = False
        with self.assertRaisesRegex(ValidationError, r"Missing " r"off-balance sheet"):
            po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))


class TestObsCommitmentWizard(PerfObligationObsCommitmentCommon):
    """Test the manual adjustment wizard."""

    def test_wizard_default_date_is_last_day_of_previous_month(self):
        """The wizard default date should be the last day of the previous month."""
        wizard = self.env["perf.obligation.obs.commitment.adjust.wizard"].create({})
        today = fields.Date.context_today(wizard)
        expected_date = today - relativedelta(months=1, day=31)
        self.assertEqual(wizard.date, expected_date)

    def test_wizard_adjusts_at_given_date(self):
        """Wizard creates adjustment entries at the chosen date."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 400, 0, po), (self.inc_pl, 0, 400, po)],
            date="2026-01-31",
        )
        obs_before = len(self._get_obs_lines(po))
        wizard = self.env["perf.obligation.obs.commitment.adjust.wizard"].create(
            {"date": "2026-01-31"}
        )
        wizard.action_adjust()
        self.assertGreater(len(self._get_obs_lines(po)), obs_before)
        self.assertAlmostEqual(self._obs_commitment_balance(po), -600)

    def test_wizard_adjustment_dated_at_wizard_date(self):
        """The adjustment entry is dated at the date chosen in the wizard."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 200, 0, po), (self.inc_pl, 0, 200, po)],
            date="2026-03-31",
        )
        wizard = self.env["perf.obligation.obs.commitment.adjust.wizard"].create(
            {"date": "2026-03-31"}
        )
        wizard.action_adjust()
        obs_lines = self._get_obs_lines(po)
        adjustment_moves = obs_lines.mapped("move_id").filtered(
            lambda m: m.date == datetime.date(2026, 3, 31)
            and any(
                line.debit > 0 and line.account_id == self.obs_income_account
                for line in m.line_ids
            )
        )
        self.assertTrue(adjustment_moves)

    def test_wizard_no_adjustment_when_balanced(self):
        """Wizard does nothing when all obligations are already balanced."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        obs_before = len(self._get_obs_lines(po))
        wizard = self.env["perf.obligation.obs.commitment.adjust.wizard"].create(
            {"date": "2026-01-31"}
        )
        wizard.action_adjust()
        self.assertEqual(len(self._get_obs_lines(po)), obs_before)


class TestObsCommitmentEndToEnd(PerfObligationObsCommitmentCommon):
    """End-to-end scenario tests: obligation lifecycle with OBS commitment tracking."""

    def test_income_obligation_full_lifecycle(self):
        """Full income lifecycle: creation → partial recognition → full recognition."""
        po = self._create_obligation(perf_type="income", total_amount=900)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self.assertAlmostEqual(self._obs_commitment_balance(po), -900)
        self.assertIsNone(po._adjust_obs_commitment(date=datetime.date(2026, 1, 1)))
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-01-31",
        )
        move1 = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNotNone(move1)
        self.assertAlmostEqual(self._obs_commitment_balance(po), -600)
        self.assertIsNone(po._adjust_obs_commitment(date=datetime.date(2026, 1, 31)))
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-02-28",
        )
        move2 = po._adjust_obs_commitment(date=datetime.date(2026, 2, 28))
        self.assertIsNotNone(move2)
        self.assertAlmostEqual(self._obs_commitment_balance(po), -300)
        self.assertIsNone(po._adjust_obs_commitment(date=datetime.date(2026, 2, 28)))
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 300, 0, po), (self.inc_pl, 0, 300, po)],
            date="2026-03-31",
        )
        move3 = po._adjust_obs_commitment(date=datetime.date(2026, 3, 31))
        self.assertIsNotNone(move3)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 0)
        self.assertIsNone(po._adjust_obs_commitment(date=datetime.date(2026, 3, 31)))

    def test_expense_obligation_full_lifecycle(self):
        """Full expense lifecycle mirrors income, using expense P&L accounts."""
        po = self._create_obligation(perf_type="expense", total_amount=600)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self.assertAlmostEqual(self._obs_commitment_balance(po), 600)
        self.assertIsNone(po._adjust_obs_commitment(date=datetime.date(2026, 1, 1)))
        self._create_and_post_move(
            self.exp_reco_journal,
            [(self.exp_pl, 200, 0, po), (self.exp_credit_bs, 0, 200, po)],
            date="2026-01-31",
        )
        move = po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertIsNotNone(move)
        self.assertAlmostEqual(self._obs_commitment_balance(po), 400)
        self.assertIsNone(po._adjust_obs_commitment(date=datetime.date(2026, 1, 31)))

    def test_obs_debit_balance_after_two_adjustments(self):
        """Two successive partial recognitions produce two adjustments and
        the commitment balance tracks correctly at each step."""
        po = self._create_obligation(perf_type="income", total_amount=1200)
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 1))
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 400, 0, po), (self.inc_pl, 0, 400, po)],
            date="2026-01-31",
        )
        po._adjust_obs_commitment(date=datetime.date(2026, 1, 31))
        self.assertAlmostEqual(self._obs_commitment_balance(po), -800)
        self._create_and_post_move(
            self.reco_journal,
            [(self.inc_debit_bs, 400, 0, po), (self.inc_pl, 0, 400, po)],
            date="2026-02-28",
        )
        po._adjust_obs_commitment(date=datetime.date(2026, 2, 28))
        self.assertAlmostEqual(self._obs_commitment_balance(po), -400)
