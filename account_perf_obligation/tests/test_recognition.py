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
        with self.assertRaisesRegex(ValidationError, r"cannot exceed"):
            wizard.action_confirm()

    def test_negative_amount_raises(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        wizard = self._create_wizard(po, -100)
        with self.assertRaisesRegex(ValidationError, r"same sign"):
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
        with self.assertRaisesRegex(UserError, r"No adjustment is needed"):
            wizard.action_confirm()

    def test_missing_config_raises(self):
        """Missing company config raises ValidationError."""
        self.company.po_income_journal_id = False
        po = self._create_obligation(perf_type="income", total_amount=100)
        wizard = self._create_wizard(po, 50)
        with self.assertRaisesRegex(
            ValidationError, r"Missing performance obligation configuration"
        ):
            wizard.action_confirm()

    def test_recognize_same_amount_twice_raises(self):
        """Recognizing the same cumulative amount again raises UserError."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        w1 = self._create_wizard(po, 500, date="2026-01-31", description="Jan")
        w1.action_confirm()
        w2 = self._create_wizard(po, 500, date="2026-02-28", description="Feb")
        with self.assertRaisesRegex(UserError, r"No adjustment is needed"):
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
        self.assertEqual(move.auto_post, "monthly")

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
        with self.assertRaisesRegex(
            ValidationError, r"No recognition at date method configured"
        ):
            po._compute_amount_to_recognize_at_date(fields.Date.today())

    def test_supports_recognition_at_date_false_by_default(self):
        """Without recognition method, _supports_recognition_at_date
        returns False."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_recognition_at_date())

    # =========================================================
    # Schedule (base)
    # =========================================================

    def test_supports_schedule_false_by_default(self):
        """Base obligation does not support schedule."""
        po = self._create_obligation(total_amount=1000.0)
        self.assertFalse(po._supports_schedule())
        self.assertFalse(po.supports_schedule)

    def test_schedule_without_support_raises(self):
        """Schedule on base obligation raises ValidationError."""
        po = self._create_obligation(total_amount=1000.0)
        with self.assertRaisesRegex(
            ValidationError, r"Schedule generation is not supported"
        ):
            po.action_generate_schedule()


class TestRecognitionNegative(TestRecognition):
    """Mirror of the 4 income scenarios with a negative total_amount.

    A negative income obligation models a credit note / revenue reversal.
    The account-swap in _get_recognition_config() means the BS sides are
    flipped compared to the positive case, but the P&L logic is identical.

    Expected behaviour:
      - amount_to_recognize=0   → full deferral on credit_bs  (now inc_debit_bs
                                   because accounts are swapped)
      - amount_to_recognize=-R  → partial recognition, unwinding the deferral
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_negative_income_obligation(self, total_amount=-1000.0):
        return self._create_obligation(perf_type="income", total_amount=total_amount)

    def _create_negative_wizard(self, po, amount, date, description):
        return self._create_wizard(po, amount, date=date, description=description)

    # ------------------------------------------------------------------
    # Basic validation
    # ------------------------------------------------------------------

    def test_negative_amount_on_negative_obligation_is_valid(self):
        """A negative amount_to_recognize is allowed when total_amount < 0."""
        po = self._create_negative_income_obligation(total_amount=-1000)
        wizard = self._create_negative_wizard(po, -100, "2026-01-31", "Jan")
        result = wizard.action_confirm()
        self.assertIn("res_id", result)

    def test_positive_amount_on_negative_obligation_raises(self):
        """A positive amount_to_recognize on a negative obligation raises."""
        po = self._create_negative_income_obligation(total_amount=-1000)
        wizard = self._create_negative_wizard(po, 100, "2026-01-31", "Jan")
        with self.assertRaisesRegex(ValidationError, r"same sign"):
            wizard.action_confirm()

    def test_negative_amount_exceeds_total_raises(self):
        """-1500 exceeds -1000 in absolute value → raises."""
        po = self._create_negative_income_obligation(total_amount=-1000)
        wizard = self._create_negative_wizard(po, -1500, "2026-01-31", "Jan")
        with self.assertRaisesRegex(ValidationError, r"cannot exceed"):
            wizard.action_confirm()

    def test_zero_amount_on_negative_obligation_is_valid(self):
        """amount_to_recognize=0 on a negative obligation is always valid."""
        po = self._create_negative_income_obligation(total_amount=-1000)
        # Post a credit note first so there is something to defer
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 0, 1000, False),
                (self.income_account, 1000, 0, po),
            ],
            date="2026-01-01",
        )
        wizard = self._create_negative_wizard(po, 0, "2026-01-31", "Jan")
        result = wizard.action_confirm()
        self.assertIn("res_id", result)

    # ------------------------------------------------------------------
    # NEGATIVE INCOME SCENARIO 1: Credit note at the beginning
    #
    # Accounts are swapped vs the positive case:
    #   debit_bs_account  → inc_credit_bs  (liability_current)
    #   credit_bs_account → inc_debit_bs   (asset_current)
    #
    # Jan: credit note -1000 posted → income balance = +1000 (debit on income)
    # m0 (recognize 0):
    #   desired income balance = -0 = 0
    #   balance_variation = -0 - (+1000) = -1000   → X < 0
    #   debit swapped-debit_bs (inc_credit_bs) 1000, credit PL 1000
    # m1 (recognize -100):
    #   desired = +100
    #   current pl_balance after m0 = +1000 - 1000 = 0  ... wait, let's think
    #   in terms of the algorithm: pl_balance is the sum of inc_pl lines ≤ date
    #   After m0: inc_pl has credit 1000  → balance = -1000
    #   balance_variation = -(-100) - (-1000) = 100 - (-1000) ...
    #
    # Let's re-derive carefully using the algorithm's own variables.
    # ------------------------------------------------------------------

    def test_negative_income_scenario1_credit_note_at_beginning(self):
        """Credit note issued upfront, recognised progressively.

        Mirrors test_income_scenario1_invoice_at_beginning with signs flipped.

        After the account swap in _get_recognition_config():
          debit_bs  → inc_credit_bs
          credit_bs → inc_debit_bs

        Step-by-step (all amounts in absolute value for readability):

        Setup: credit note -1000 on income_account
          → income_account balance (debit) = +1000
          → inc_pl balance = 0

        m0 (recognize 0):
          pl_balance   = 0                      (no inc_pl lines yet)
          desired      = -(-0) = 0              (is_income: DI = -R = 0)
          variation    = 0 - 0 = 0 ... hmm

        Actually the income_account is NOT inc_pl.
        inc_pl is the *recognition* P&L account.
        income_account is the *invoice* P&L account.
        _get_income_or_expense_balance reads lines on accounts whose
        internal_group == "income", which includes BOTH.

        So after posting the credit note on income_account:
          pl_balance at 2026-01-31 = +1000  (debit 1000 on income_account)

        m0 (recognize 0):
          pl_balance   = +1000
          variation    = -0 - 1000 = -1000   → X < 0
          debit swapped-debit_bs (inc_credit_bs) 1000, credit inc_pl 1000
          → inc_credit_bs balance = +1000 (debit)
          → inc_pl credit 1000

        m1 (recognize -100, i.e. cumulative -100):
          pl_balance at 2026-02-28:
            income_account: +1000 (debit from credit note)
            inc_pl:         -1000 (credit from m0)
            total:          0
          variation = -(-100) - 0 = +100  → X > 0
          unwind inc_credit_bs (positive balance +1000): credit 100
          inc_pl debit 100
          → inc_credit_bs balance = +900

        m2 (recognize -200):
          pl_balance at 2026-03-31:
            income_account: +1000
            inc_pl:         -1000 + 100 = -900
            total:          +100
          variation = -(-200) - 100 = +100  → X > 0
          unwind inc_credit_bs (balance +900): credit 100
          inc_pl debit 100
          → inc_credit_bs balance = +800
        """
        po = self._create_negative_income_obligation(total_amount=-1000)

        # Post a credit note: debit income_account (reversal of revenue)
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 0, 1000, False),
                (self.income_account, 1000, 0, po),
            ],
            date="2026-01-01",
        )

        # --- m0: recognize 0 ---
        result = self._create_negative_wizard(
            po, 0, "2026-01-31", "Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        # swapped debit_bs is inc_credit_bs; credit_bs is inc_debit_bs
        swapped_debit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_debit_bs.debit, 1000)
        self.assertAlmostEqual(pl.credit, 1000)
        self._assert_bs(
            po,
            "2026-01-31",
            self.inc_credit_bs,
            1000,  # swapped debit_bs has positive balance
            self.inc_debit_bs,
            0,
        )

        # --- m1: recognize -100 ---
        result = self._create_negative_wizard(
            po, -100, "2026-02-28", "Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_debit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-02-28",
            self.inc_credit_bs,
            900,
            self.inc_debit_bs,
            0,
        )

        # --- m2: recognize -200 ---
        result = self._create_negative_wizard(
            po, -200, "2026-03-31", "Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_debit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-03-31",
            self.inc_credit_bs,
            800,
            self.inc_debit_bs,
            0,
        )

    # ------------------------------------------------------------------
    # NEGATIVE INCOME SCENARIO 2: Credit note at the end
    #
    # No credit note yet; recognize progressively; credit note arrives last.
    #
    # m0 (recognize -100, no credit note yet):
    #   pl_balance = 0
    #   variation  = -(-100) - 0 = +100  → X > 0
    #   no positive BS balance to unwind
    #   credit swapped-credit_bs (inc_debit_bs) 100, debit inc_pl 100
    #   → inc_debit_bs balance = -100 (credit)
    #
    # m1 (recognize -200):
    #   pl_balance at date: inc_pl debit 100 → balance = +100
    #   variation = -(-200) - 100 = +100  → X > 0
    #   credit inc_debit_bs 100, debit inc_pl 100
    #   → inc_debit_bs = -200
    #
    # m2 (recognize -300):
    #   pl_balance: inc_pl debit 200 → +200
    #   variation = 300 - 200 = +100  → X > 0
    #   credit inc_debit_bs 100, debit inc_pl 100
    #   → inc_debit_bs = -300
    #
    # Credit note -300 posted Apr 15.
    #
    # m3 (recognize -300 again):
    #   pl_balance at Apr 30:
    #     income_account: +300 (debit from credit note)
    #     inc_pl:         +300 (debit, 3 × 100)
    #     total:          +600  wait — we need to think again.
    #   Actually inc_pl *balance* = sum of (debit - credit) on inc_pl lines.
    #   inc_pl has debit 100 + 100 + 100 = 300 → balance = +300
    #   income_account has debit 300 → balance = +300
    #   total pl_balance = +600
    #   variation = -(-300) - 600 = 300 - 600 = -300  → X < 0
    #   unwind inc_debit_bs (negative balance -300): debit 300
    #   credit inc_pl 300
    #   → inc_debit_bs = 0
    # ------------------------------------------------------------------

    def test_negative_income_scenario2_credit_note_at_end(self):
        """Recognize before credit note arrives, then credit note comes.

        Mirrors test_income_scenario2_invoice_at_end with signs flipped.
        swapped credit_bs = inc_debit_bs (asset_current).
        """
        po = self._create_negative_income_obligation(total_amount=-300)

        # --- m0: recognize -100 ---
        result = self._create_negative_wizard(
            po, -100, "2026-01-31", "Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-01-31",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            -100,  # credit balance → negative
        )

        # --- m1: recognize -200 ---
        result = self._create_negative_wizard(
            po, -200, "2026-02-28", "Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-02-28",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            -200,
        )

        # --- m2: recognize -300 ---
        result = self._create_negative_wizard(
            po, -300, "2026-03-31", "Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-03-31",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            -300,
        )

        # Credit note -300 on Apr 15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 0, 300, False),
                (self.income_account, 300, 0, po),
            ],
            date="2026-04-15",
        )

        # --- m3: recognize -300 (settlement) ---
        result = self._create_negative_wizard(
            po, -300, "2026-04-30", "Apr"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_credit_bs.debit, 300)
        self.assertAlmostEqual(pl.credit, 300)
        self._assert_bs(
            po,
            "2026-04-30",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            0,
        )

    # ------------------------------------------------------------------
    # NEGATIVE INCOME SCENARIO 4: Credit note in the middle (mixed)
    #
    # m0 (recognize -100): variation +100 → credit inc_debit_bs 100, debit pl 100
    # m1 (recognize -200): variation +100 → credit inc_debit_bs 100, debit pl 100
    # Credit note -400 on Mar 15.
    # m2 (recognize -300):
    #   pl_balance at Mar 31:
    #     income_account: +400
    #     inc_pl: +200  (debit 200)
    #     total: +600
    #   variation = -(-300) - 600 = 300 - 600 = -300  → X < 0
    #   unwind inc_debit_bs (balance -200, negative): debit 200 (up to 300)
    #   remaining = 100 → debit swapped-debit_bs (inc_credit_bs) 100
    #   credit inc_pl 300
    #   → inc_debit_bs = 0, inc_credit_bs = +100
    # m3 (recognize -400):
    #   pl_balance at Apr 30:
    #     income_account: +400
    #     inc_pl: -300 + 300 = ... let's count debits/credits on inc_pl:
    #       m0: debit 100, m1: debit 100, m2: credit 300  → balance = -100
    #     total: +400 - 100 = +300
    #   variation = -(-400) - 300 = 400 - 300 = +100  → X > 0
    #   unwind inc_credit_bs (balance +100, positive): credit 100
    #   inc_pl debit 100
    #   → inc_credit_bs = 0, inc_debit_bs = 0
    # ------------------------------------------------------------------

    def test_negative_income_scenario4_credit_note_in_middle(self):
        """Credit note arrives mid-stream, creating a mixed BS adjustment.

        Mirrors test_income_scenario4_invoice_in_middle with signs flipped.
        """
        po = self._create_negative_income_obligation(total_amount=-400)

        # --- m0: recognize -100 ---
        result = self._create_negative_wizard(
            po, -100, "2026-01-31", "Jan"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-01-31",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            -100,
        )

        # --- m1: recognize -200 ---
        result = self._create_negative_wizard(
            po, -200, "2026-02-28", "Feb"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_credit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-02-28",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            -200,
        )

        # Credit note -400 on Mar 15
        self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, 0, 400, False),
                (self.income_account, 400, 0, po),
            ],
            date="2026-03-15",
        )

        # --- m2: recognize -300 (mixed!) ---
        result = self._create_negative_wizard(
            po, -300, "2026-03-31", "Mar"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_credit_bs = self._filter_lines(lines, self.inc_debit_bs)
        swapped_debit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 3)
        self.assertAlmostEqual(swapped_credit_bs.debit, 200)  # unwind negative BS
        self.assertAlmostEqual(swapped_debit_bs.debit, 100)  # new positive BS
        self.assertAlmostEqual(pl.credit, 300)
        self._assert_bs(
            po,
            "2026-03-31",
            self.inc_credit_bs,
            100,
            self.inc_debit_bs,
            0,
        )

        # --- m3: recognize -400 ---
        result = self._create_negative_wizard(
            po, -400, "2026-04-30", "Apr"
        ).action_confirm()
        lines = self.env["account.move"].browse(result["res_id"]).line_ids

        swapped_debit_bs = self._filter_lines(lines, self.inc_credit_bs)
        pl = self._filter_lines(lines, self.inc_pl)
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(swapped_debit_bs.credit, 100)
        self.assertAlmostEqual(pl.debit, 100)
        self._assert_bs(
            po,
            "2026-04-30",
            self.inc_credit_bs,
            0,
            self.inc_debit_bs,
            0,
        )
