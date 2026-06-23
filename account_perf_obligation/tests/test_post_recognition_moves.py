# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, fields
from odoo.exceptions import UserError

from .common import PerfObligationCommon


class TestPostRecognitionMoves(PerfObligationCommon):
    """Test the posting workflow for recognition moves."""

    def _create_draft_move_in_journal(
        self, journal, perf_obligation=None, date="2026-01-15"
    ):
        """Create a draft move in a non-recognition journal with or without
        a perf obligation line."""
        lines = [
            Command.create(
                {
                    "account_id": self.receivable_account.id,
                    "debit": 100,
                    "credit": 0,
                    "name": "Test",
                }
            ),
            Command.create(
                {
                    "account_id": self.income_account.id,
                    "debit": 0,
                    "credit": 100,
                    "name": "Test",
                    "perf_obligation_id": perf_obligation.id
                    if perf_obligation
                    else False,
                }
            ),
        ]
        return self.env["account.move"].create(
            {
                "journal_id": journal.id,
                "date": date,
                "line_ids": lines,
            }
        )

    def test_get_recognition_journals_single_company(self):
        """_get_recognition_journals returns both income and expense
        recognition journals for the company."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        journals = po._get_recognition_journals()
        self.assertIn(self.reco_journal, journals)
        self.assertIn(self.exp_reco_journal, journals)

    def test_get_recognition_journals_missing_config_raises(self):
        """_get_recognition_journals returns only configured journals."""
        self.company.po_income_journal_id = False
        po = self._create_obligation(perf_type="income", total_amount=1000)
        journals = po._get_recognition_journals()
        self.assertNotIn(self.reco_journal, journals)
        self.assertIn(self.exp_reco_journal, journals)

    def test_no_blocking_when_no_draft_moves(self):
        """No error when there are no draft moves."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        # Should not raise
        po._check_blocking_draft_moves(fields.Date.today())

    def test_no_blocking_when_draft_move_has_no_perf_obligation(self):
        """Draft moves without perf obligation lines do not block."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_draft_move_in_journal(self.sale_journal, perf_obligation=None)
        # Should not raise
        po._check_blocking_draft_moves(fields.Date.today())

    def test_no_blocking_when_draft_move_in_recognition_journal_income(self):
        """Draft moves in the income recognition journal do not block."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.env["account.move"].create(
            {
                "journal_id": self.reco_journal.id,
                "date": "2026-01-15",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.inc_debit_bs.id,
                            "debit": 100,
                            "credit": 0,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.inc_pl.id,
                            "debit": 0,
                            "credit": 100,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                ],
            }
        )
        # Should not raise
        po._check_blocking_draft_moves(fields.Date.today())

    def test_no_blocking_when_draft_move_in_recognition_journal_expense(self):
        """Draft moves in the expense recognition journal do not block."""
        po = self._create_obligation(perf_type="expense", total_amount=1000)
        self.env["account.move"].create(
            {
                "journal_id": self.exp_reco_journal.id,
                "date": "2026-01-15",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.exp_debit_bs.id,
                            "debit": 100,
                            "credit": 0,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.exp_pl.id,
                            "debit": 0,
                            "credit": 100,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        }
                    ),
                ],
            }
        )
        # Should not raise
        po._check_blocking_draft_moves(fields.Date.today())

    def test_no_blocking_when_draft_move_dated_after_check_date(self):
        """Draft moves dated after the check date do not block."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-02-01"
        )
        # Check at 2026-01-31: the draft move on 2026-02-01 is after, so no block
        po._check_blocking_draft_moves(fields.Date.from_string("2026-01-31"))

    def test_no_blocking_when_draft_move_posted(self):
        """Posted moves (in any journal) do not block."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        move = self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        move.action_post()
        # Should not raise
        po._check_blocking_draft_moves(fields.Date.today())

    def test_blocking_when_draft_move_in_non_reco_journal(self):
        """Draft moves with perf obligation lines in non-recognition
        journals block posting."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        with self.assertRaisesRegex(UserError, r"Cannot post performance obligation"):
            po._check_blocking_draft_moves(fields.Date.today())

    def test_blocking_error_lists_all_blocking_moves(self):
        """Error message lists all blocking moves."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-20"
        )
        with self.assertRaisesRegex(
            UserError, r"Cannot post performance obligation"
        ) as cm:
            po._check_blocking_draft_moves(fields.Date.today())
        error_msg = str(cm.exception)
        # Both move identifiers should appear in the message
        self.assertIn(self.sale_journal.display_name, error_msg)

    def test_action_post_recognition_moves_single_move(self):
        """action_post_recognition_moves posts a single draft recognition move."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move = po._recognize(500, "2026-01-31", "Test")
        self.assertEqual(move.state, "draft")
        po.action_post_recognition_moves(fields.Date.from_string("2026-01-31"))
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move.state, "posted")

    def test_action_post_recognition_moves_multiple_moves(self):
        """action_post_recognition_moves posts all eligible draft recognition
        moves up to date, and leaves later ones untouched."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move1 = po._recognize(300, "2026-01-31", "Jan")
        move2 = po._recognize(600, "2026-02-28", "Feb")
        move3 = po._recognize(1000, "2026-03-31", "Mar")
        po.action_post_recognition_moves(fields.Date.from_string("2026-02-28"))
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move1.state, "posted")
        self.assertEqual(move2.state, "posted")
        self.assertEqual(move3.state, "draft")  # not marked, date is after

    def test_action_post_recognition_moves_respects_date_filter(self):
        """action_post_recognition_moves only marks/posts moves dated on or
        before the given date."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move_early = po._recognize(300, "2026-01-15", "Early")
        move_late = po._recognize(600, "2026-02-15", "Late")
        po.action_post_recognition_moves(fields.Date.from_string("2026-01-31"))
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move_early.state, "posted")
        self.assertEqual(move_late.state, "draft")

    def test_action_post_recognition_moves_noop_when_no_draft_moves(self):
        """action_post_recognition_moves is a no-op when no draft moves exist."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        # Should not raise
        po.action_post_recognition_moves(fields.Date.today())

    def test_post_recognition_moves_only_recognition_journal(self):
        """_post_recognition_moves's search only targets moves in the
        recognition journal, even when other journals have draft moves
        with perf obligation lines."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        other_move = self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        reco_move = po._recognize(500, "2026-01-31", "Test")
        reco_journals = po._get_recognition_journals()
        matched_moves = self.env["account.move"].search(
            [
                ("journal_id", "in", reco_journals.ids),
                ("state", "=", "draft"),
                ("date", "<=", fields.Date.today()),
                ("line_ids.perf_obligation_id", "=", po.id),
            ]
        )
        self.assertIn(reco_move, matched_moves)
        self.assertNotIn(other_move, matched_moves)
        self.assertEqual(other_move.state, "draft")

    def test_action_post_recognition_moves_checks_blocking_first(self):
        """action_post_recognition_moves checks for blocking draft moves
        before posting anything."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        # Create a blocking draft move
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        # Create a recognition move
        reco_move = po._recognize(500, "2026-01-31", "Test")
        with self.assertRaisesRegex(UserError, r"Cannot post performance obligation"):
            po.action_post_recognition_moves(fields.Date.from_string("2026-01-31"))
        # Nothing should be posted
        self.assertEqual(reco_move.state, "draft")

    def test_action_post_recognition_moves_respects_date(self):
        """action_post_recognition_moves respects the date filter."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move_early = po._recognize(300, "2026-01-15", "Early")
        move_late = po._recognize(600, "2026-02-15", "Late")
        po.action_post_recognition_moves(fields.Date.from_string("2026-01-31"))
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move_early.state, "posted")
        self.assertEqual(move_late.state, "draft")

    def test_post_blocked_when_blocking_draft_move_exists(self):
        """Posting a recognition move directly (e.g. via auto_post cron)
        is blocked if a non-reco draft move exists."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move = po._recognize(500, "2026-01-31", "Test")
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        with self.assertRaisesRegex(UserError, r"Cannot post performance obligation"):
            move.action_post()

    def test_post_all_posts_across_obligations(self):
        po1 = self._create_obligation(perf_type="income", total_amount=1000)
        po2 = self._create_obligation(perf_type="income", total_amount=1000)
        for po in (po1, po2):
            self._create_and_post_move(
                self.sale_journal,
                [
                    (self.receivable_account, po.total_amount, 0, False),
                    (self.income_account, 0, po.total_amount, po),
                ],
            )
        move1 = po1._recognize(500, "2026-01-31", "Test")
        move2 = po2._recognize(500, "2026-01-31", "Test")
        self.env["perf.obligation"]._post_all_recognition_moves(
            fields.Date.from_string("2026-01-31")
        )
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move1.state, "posted")
        self.assertEqual(move2.state, "posted")

    def test_post_all_respects_date(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move_early = po._recognize(300, "2026-01-15", "Early")
        move_late = po._recognize(600, "2026-02-15", "Late")
        self.env["perf.obligation"]._post_all_recognition_moves(
            fields.Date.from_string("2026-01-31")
        )
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move_early.state, "posted")
        self.assertEqual(move_late.state, "draft")

    def test_post_all_checks_blocking(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move = po._recognize(500, "2026-01-31", "Test")
        self._create_draft_move_in_journal(
            self.sale_journal, perf_obligation=po, date="2026-01-15"
        )
        with self.assertRaisesRegex(UserError, r"Cannot post performance obligation"):
            self.env["perf.obligation"]._post_all_recognition_moves(
                fields.Date.from_string("2026-01-31")
            )
        self.assertEqual(move.state, "draft")

    def test_post_all_noop_when_no_draft_moves(self):
        # Should not raise
        self.env["perf.obligation"]._post_all_recognition_moves(fields.Date.today())

    def test_wizard_without_obligations_posts_all(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        move = po._recognize(500, "2026-01-31", "Test")
        wizard = self.env["perf.obligation.post.recognition.moves"].create(
            {
                "date": "2026-01-31",
                # no perf_obligation_ids provided
            }
        )
        wizard.action_confirm()
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move.state, "posted")

    def test_wizard_with_obligations_posts_selected_only(self):
        po1 = self._create_obligation(perf_type="income", total_amount=1000)
        po2 = self._create_obligation(perf_type="income", total_amount=1000)
        for po in (po1, po2):
            self._create_and_post_move(
                self.sale_journal,
                [
                    (self.receivable_account, 1000, 0, False),
                    (self.income_account, 0, 1000, po),
                ],
            )
        move1 = po1._recognize(500, "2026-01-31", "Test 1")
        move2 = po2._recognize(500, "2026-01-31", "Test 2")

        wizard = self.env["perf.obligation.post.recognition.moves"].create(
            {
                "perf_obligation_ids": [Command.set(po1.ids)],
                "date": "2026-01-31",
            }
        )
        wizard.action_confirm()
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move1.state, "posted")
        self.assertEqual(move2.state, "draft")
