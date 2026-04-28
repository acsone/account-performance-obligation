# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError

from .common import PerfObligationCommon


class TestRecognition(PerfObligationCommon):
    """Test the recognition algorithm against the 4 reference scenarios
    and the expense mirror cases."""

    def _assert_bs(
        self, po, date, debit_bs_account, debit_bs, credit_bs_account, credit_bs
    ):
        """Assert both BS balances in one call."""
        self.assertAlmostEqual(
            self._get_bs_balance(po, debit_bs_account, date),
            debit_bs,
            msg=f"debit_bs at {date}",
        )
        self.assertAlmostEqual(
            self._get_bs_balance(po, credit_bs_account, date),
            credit_bs,
            msg=f"credit_bs at {date}",
        )

    # =========================================================
    # Model basics
    # =========================================================

    def test_sequence_on_create(self):
        """Name is auto-generated from sequence."""
        po = self._create_obligation()
        self.assertNotEqual(po.name, "/")
        self.assertTrue(po.name)

    def test_move_line_count(self):
        """move_line_count reflects linked non-cancelled lines."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self.assertEqual(po.move_line_count, 0)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        po.invalidate_recordset()
        self.assertEqual(po.move_line_count, 1)

    def test_action_view_move_lines(self):
        """action_view_move_lines returns correct action."""
        po = self._create_obligation()
        action = po.action_view_move_lines()
        self.assertEqual(action["res_model"], "account.move.line")
        self.assertIn(("perf_obligation_id", "=", po.id), action["domain"])

    # =========================================================
    # Validation
    # =========================================================

    def test_amount_exceeds_total_raises(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        wizard = self._create_wizard(po, 1500)
        with self.assertRaises(ValidationError):
            wizard.action_confirm()

    def test_negative_amount_raises(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        wizard = self._create_wizard(po, -100)
        with self.assertRaises(ValidationError):
            wizard.action_confirm()

    def test_no_adjustment_needed_raises(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )
        wizard = self._create_wizard(po, 1000)
        with self.assertRaises(UserError):
            wizard.action_confirm()

    def test_missing_config_raises(self):
        """Missing company config raises ValidationError."""
        self.company.po_income_journal_id = False
        po = self._create_obligation(perf_type="income", total_amount=100)
        wizard = self._create_wizard(po, 50)
        with self.assertRaises(ValidationError):
            wizard.action_confirm()

    def test_recognize_same_amount_twice_raises(self):
        """Recognizing the same cumulative amount again raises UserError."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        w1 = self._create_wizard(po, 500, date="2026-01-31", description="Jan")
        w1.action_confirm()
        w2 = self._create_wizard(po, 500, date="2026-02-28", description="Feb")
        with self.assertRaises(UserError):
            w2.action_confirm()

    # =========================================================
    # Constraints
    # =========================================================

    def test_perf_obligation_on_invalid_account_raises(self):
        """Setting perf_obligation_id on a receivable line raises."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        with self.assertRaises(ValidationError):
            self.env["account.move"].create(
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
                                "perf_obligation_id": po.id,
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

    def test_perf_obligation_on_valid_accounts(self):
        """Setting perf_obligation_id on income/expense/current accounts works."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        move = self.env["account.move"].create(
            {
                "journal_id": self.reco_journal.id,
                "date": "2026-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.inc_debit_bs.id,
                            "debit": 100,
                            "credit": 0,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        },
                    ),
                    Command.create(
                        {
                            "account_id": self.inc_pl.id,
                            "debit": 0,
                            "credit": 100,
                            "name": "Test",
                            "perf_obligation_id": po.id,
                        },
                    ),
                ],
            }
        )
        self.assertTrue(move)

    # =========================================================
    # Metadata
    # =========================================================

    def test_move_metadata_and_labels(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
        )

        wizard = self._create_wizard(po, 500, date="2025-02-28", description="Feb reco")
        result = wizard.action_confirm()
        move = self.env["account.move"].browse(result["res_id"])

        self.assertEqual(str(move.date), "2025-02-28")
        self.assertEqual(move.ref, f"{po.name} - Feb reco")
        self.assertEqual(move.journal_id, self.reco_journal)
        self.assertEqual(move.state, "draft")
        self.assertEqual(move.auto_post, "at_date")

        for line in move.line_ids:
            self.assertEqual(line.name, "Feb reco")
            self.assertEqual(line.perf_obligation_id, po)

    # =========================================================
    # INCOME SCENARIO 1: Invoice at the beginning
    # =========================================================

    def test_income_scenario1_invoice_at_beginning(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)

        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 1000, 0, False),
                (self.income_account, 0, 1000, po),
            ],
            date="2026-01-01",
        )

        # --- m0: recognize 0 ---
        result = self._create_wizard(
            po, 0, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.credit, 1000)
        self.assertAlmostEqual(pl.debit, 1000)
        self._assert_bs(
            po, "2026-01-31", self.inc_debit_bs, 0, self.inc_credit_bs, -1000
        )

        # --- m1: recognize 100 ---
        result = self._create_wizard(
            po, 100, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(
            po, "2026-02-28", self.inc_debit_bs, 0, self.inc_credit_bs, -900
        )

        # --- m2: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(
            po, "2026-03-31", self.inc_debit_bs, 0, self.inc_credit_bs, -800
        )

    # =========================================================
    # INCOME SCENARIO 2: Invoice at the end
    # =========================================================

    def test_income_scenario2_invoice_at_end(self):
        po = self._create_obligation(perf_type="income", total_amount=300)

        # --- m0: recognize 100 ---
        result = self._create_wizard(
            po, 100, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(po, "2026-01-31", self.inc_debit_bs, 100, self.inc_credit_bs, 0)

        # --- m1: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(po, "2026-02-28", self.inc_debit_bs, 200, self.inc_credit_bs, 0)

        # --- m2: recognize 300 ---
        result = self._create_wizard(
            po, 300, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self._assert_bs(po, "2026-03-31", self.inc_debit_bs, 300, self.inc_credit_bs, 0)

        # Invoice 300 on Apr 15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 300, 0, False),
                (self.income_account, 0, 300, po),
            ],
            date="2026-04-15",
        )

        # --- m3: recognize 300 ---
        result = self._create_wizard(
            po, 300, date="2026-04-30", description="Apr"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.credit, 300)
        self.assertAlmostEqual(pl.debit, 300)
        self._assert_bs(po, "2026-04-30", self.inc_debit_bs, 0, self.inc_credit_bs, 0)

    # =========================================================
    # INCOME SCENARIO 3: Regular invoices
    # =========================================================

    def test_income_scenario3_regular_invoices(self):
        po = self._create_obligation(perf_type="income", total_amount=400)

        # --- m0: recognize 100 ---
        result = self._create_wizard(
            po, 100, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(po, "2026-01-31", self.inc_debit_bs, 100, self.inc_credit_bs, 0)

        # Invoice 200 on Feb 15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 200, 0, False),
                (self.income_account, 0, 200, po),
            ],
            date="2026-02-15",
        )

        # --- m1: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(po, "2026-02-28", self.inc_debit_bs, 0, self.inc_credit_bs, 0)

        # --- m2: recognize 300 ---
        result = self._create_wizard(
            po, 300, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(po, "2026-03-31", self.inc_debit_bs, 100, self.inc_credit_bs, 0)

        # Invoice 200 on Apr 15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 200, 0, False),
                (self.income_account, 0, 200, po),
            ],
            date="2026-04-15",
        )

        # --- m3: recognize 400 ---
        result = self._create_wizard(
            po, 400, date="2026-04-30", description="Apr"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertAlmostEqual(debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(po, "2026-04-30", self.inc_debit_bs, 0, self.inc_credit_bs, 0)

    # =========================================================
    # INCOME SCENARIO 4: Invoice in the middle (mixed)
    # =========================================================

    def test_income_scenario4_invoice_in_middle(self):
        po = self._create_obligation(perf_type="income", total_amount=400)

        # --- m0: recognize 100 ---
        result = self._create_wizard(
            po, 100, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self._assert_bs(po, "2026-01-31", self.inc_debit_bs, 100, self.inc_credit_bs, 0)

        # --- m1: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self._assert_bs(po, "2026-02-28", self.inc_debit_bs, 200, self.inc_credit_bs, 0)

        # Invoice 400 on Mar 15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 400, 0, False),
                (self.income_account, 0, 400, po),
            ],
            date="2026-03-15",
        )

        # --- m2: recognize 300 (mixed!) ---
        result = self._create_wizard(
            po, 300, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.inc_debit_bs)
        credit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(debit_bs.credit, 200)
        self.assertAlmostEqual(credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 300)
        self._assert_bs(
            po, "2026-03-31", self.inc_debit_bs, 0, self.inc_credit_bs, -100
        )

        # --- m3: recognize 400 ---
        result = self._create_wizard(
            po, 400, date="2026-04-30", description="Apr"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 100)
        self._assert_bs(po, "2026-04-30", self.inc_debit_bs, 0, self.inc_credit_bs, 0)

    # =========================================================
    # EXPENSE SCENARIO 1: Bill at the beginning
    # =========================================================

    def test_expense_scenario1_bill_at_beginning(self):
        po = self._create_obligation(perf_type="expense", total_amount=1000)

        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 1000, False),
                (self.expense_account, 1000, 0, po),
            ],
            date="2026-01-01",
        )

        # --- m0: recognize 0 ---
        result = self._create_wizard(
            po, 0, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.exp_debit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.debit, 1000)
        self.assertAlmostEqual(pl.credit, 1000)
        self._assert_bs(
            po, "2026-01-31", self.exp_debit_bs, 1000, self.exp_credit_bs, 0
        )

        # --- m1: recognize 100 ---
        result = self._create_wizard(
            po, 100, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.exp_debit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(po, "2026-02-28", self.exp_debit_bs, 900, self.exp_credit_bs, 0)

        # --- m2: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.exp_debit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(po, "2026-03-31", self.exp_debit_bs, 800, self.exp_credit_bs, 0)

    # =========================================================
    # EXPENSE SCENARIO 2: Bill at the end
    # =========================================================

    def test_expense_scenario2_bill_at_end(self):
        """Recognize before bill arrives, then bill comes."""
        po = self._create_obligation(perf_type="expense", total_amount=300)

        # --- m0: recognize 100, no bill ---
        result = self._create_wizard(
            po, 100, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.exp_credit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po, "2026-01-31", self.exp_debit_bs, 0, self.exp_credit_bs, -100
        )

        # --- m1: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.exp_credit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertAlmostEqual(credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po, "2026-02-28", self.exp_debit_bs, 0, self.exp_credit_bs, -200
        )

        # Bill 300 on Mar 15
        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 300, False),
                (self.expense_account, 300, 0, po),
            ],
            date="2026-03-15",
        )

        # --- m2: recognize 300 ---
        result = self._create_wizard(
            po, 300, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.exp_credit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.debit, 200)
        self.assertAlmostEqual(pl.credit, 200)
        self._assert_bs(po, "2026-03-31", self.exp_debit_bs, 0, self.exp_credit_bs, 0)

    # =========================================================
    # EXPENSE SCENARIO 4: Bill in the middle (mixed)
    # =========================================================

    def test_expense_scenario4_bill_in_middle(self):
        po = self._create_obligation(perf_type="expense", total_amount=400)

        # --- m0: recognize 100 ---
        result = self._create_wizard(
            po, 100, date="2026-01-31", description="Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.exp_credit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po, "2026-01-31", self.exp_debit_bs, 0, self.exp_credit_bs, -100
        )

        # --- m1: recognize 200 ---
        result = self._create_wizard(
            po, 200, date="2026-02-28", description="Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.exp_credit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertAlmostEqual(credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po, "2026-02-28", self.exp_debit_bs, 0, self.exp_credit_bs, -200
        )

        # Bill 400 on Mar 15
        self._create_and_post_move(
            self.purchase_journal,
            [
                (self.payable_account, 0, 400, False),
                (self.expense_account, 400, 0, po),
            ],
            date="2026-03-15",
        )

        # --- m2: recognize 300 (mixed!) ---
        result = self._create_wizard(
            po, 300, date="2026-03-31", description="Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        credit_bs = self._filter_lines(lines, self.exp_credit_bs)
        debit_bs = self._filter_lines(lines, self.exp_debit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(credit_bs.debit, 200)
        self.assertAlmostEqual(debit_bs.debit, 100)
        self.assertAlmostEqual(pl.credit, 300)
        self._assert_bs(po, "2026-03-31", self.exp_debit_bs, 100, self.exp_credit_bs, 0)

        # --- m3: recognize 400 ---
        result = self._create_wizard(
            po, 400, date="2026-04-30", description="Apr"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        debit_bs = self._filter_lines(lines, self.exp_debit_bs)
        pl = self._filter_lines(lines, self.exp_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(po, "2026-04-30", self.exp_debit_bs, 0, self.exp_credit_bs, 0)

    # =========================================================
    # Recognition at date (base)
    # =========================================================

    def test_no_recognition_method_raises(self):
        """Without recognition method, _compute_amount_to_recognize_at_date
        raises ValidationError."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po.recognition_at_date_method)
        with self.assertRaises(ValidationError):
            po._compute_amount_to_recognize_at_date(fields.Date.today())

    def test_supports_recognition_at_date_false_by_default(self):
        """Without recognition method, _supports_recognition_at_date
        returns False."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_recognition_at_date())

    # =========================================================
    # Forecast (base)
    # =========================================================

    def test_supports_forecast_false_by_default(self):
        """Base obligation does not support forecast."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_forecast())

    def test_forecast_without_support_raises(self):
        """Forecast on base obligation raises ValidationError."""
        po = self._create_obligation(total_amount=1000.0)
        with self.assertRaises(ValidationError):
            po.action_generate_forecast()
