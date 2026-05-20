# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestContractPerfObligation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.contract_template = cls.env["contract.template"].create(
            {"name": "Test Contract Template"}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Plain Contract Product",
                "type": "service",
            }
        )

    def _make_contract(self, *lines, contract_type="sale"):
        """Build a contract with lines.
        Each line is (product, qty, price_unit, date_start, date_end, autocreate).
        """
        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": self.partner.id,
                "contract_type": contract_type,
                "line_recurrence": True,
            }
        )
        for product, qty, price, date_start, date_end, autocreate in lines:
            self.env["contract.line"].create(
                {
                    "contract_id": contract.id,
                    "product_id": product.id,
                    "name": product.name,
                    "quantity": qty,
                    "price_unit": price,
                    "date_start": date_start,
                    "date_end": date_end,
                    "recurring_next_date": date_start,
                    "recurring_interval": 1,
                    "recurring_rule_type": "monthly",
                    "recurring_invoicing_type": "pre-paid",
                    "uom_id": product.uom_id.id,
                    "perf_obligation_auto_create": autocreate,
                }
            )
        return contract

    def _make_purchase_contract_line(self, product, autocreate=True):
        """Helper to create a single-line purchase contract."""
        return self._make_contract(
            (
                product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                autocreate,
            ),
            contract_type="purchase",
        )

    # ------------------------------------------------------------------
    # Obligation creation
    # ------------------------------------------------------------------

    def test_contract_method_creates_obligation(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        self.assertEqual(len(line.perf_obligation_ids), 1)
        po = line.perf_obligation_ids
        self.assertEqual(po.perf_type, "income")
        self.assertEqual(po.start_date, fields.Date.from_string("2026-01-01"))
        self.assertEqual(po.end_date, fields.Date.from_string("2026-12-31"))
        self.assertEqual(po.recognition_at_date_method, "daily")
        self.assertEqual(po.contract_line_id, line)

    def test_total_amount_computed_from_quantity_and_price(self):
        contract = self._make_contract(
            (
                self.product,
                3,
                400.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.total_amount, 3 * 400.0)

    def test_plain_product_no_obligation(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                False,
            )
        )
        self.assertFalse(contract.contract_line_ids.perf_obligation_ids)

    def test_obligation_linked_to_contract_line(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        self.assertEqual(line.perf_obligation_ids.contract_line_id, line)

    def test_duplicate_guard(self):
        """Calling _create_perf_obligation_if_needed again updates the existing
        obligation instead of creating a duplicate."""
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        line._create_perf_obligation_if_needed()
        self.assertEqual(len(line.perf_obligation_ids), 1)

    # ------------------------------------------------------------------
    # Smart button count
    # ------------------------------------------------------------------

    def test_perf_obligation_count(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            ),
            (
                self.product,
                1,
                800.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-06-30"),
                True,
            ),
        )
        self.assertEqual(contract.perf_obligation_count, 2)

    def test_perf_obligation_count_excludes_plain_lines(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            ),
            (
                self.product,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                False,
            ),
        )
        self.assertEqual(contract.perf_obligation_count, 1)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def test_cancel_sets_total_amount_to_zero_when_nothing_invoiced(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_ids
        self.assertEqual(po.total_amount, 1200.0)
        line.write({"is_canceled": True})
        self.assertEqual(po.total_amount, 0.0)

    def test_cancel_posts_chatter_message(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_ids
        msg_count_before = len(po.message_ids)
        line.write({"is_canceled": True})
        self.assertGreater(len(po.message_ids), msg_count_before)

    def test_cancel_plain_line_no_error(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                False,
            )
        )
        line = contract.contract_line_ids
        line.write({"is_canceled": True})  # must not raise

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def test_unlink_deletes_obligation(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_ids
        po_id = po.id
        line.write({"is_canceled": True})
        line.unlink()
        self.assertFalse(self.env["perf.obligation"].browse(po_id).exists())

    def test_unlink_blocked_by_posted_move(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_ids
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 1200.0,
                            "perf_obligation_id": po.id,
                        },
                    )
                ],
            }
        )
        move.action_post()
        line.write({"is_canceled": True})
        with self.assertRaises(UserError):
            line.unlink()

    def test_unlink_deletes_draft_moves(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_ids
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "journal_id": journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 1200.0,
                            "perf_obligation_id": po.id,
                        },
                    )
                ],
            }
        )
        move_id = move.id
        self.assertEqual(move.state, "draft")
        line.write({"is_canceled": True})
        line.unlink()
        self.assertFalse(self.env["account.move"].browse(move_id).exists())

    # ------------------------------------------------------------------
    # Invoice line propagation
    # ------------------------------------------------------------------

    def test_prepare_invoice_line_carries_obligation(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        vals = line._prepare_invoice_line()
        self.assertEqual(vals.get("perf_obligation_id"), line.perf_obligation_ids[0].id)

    def test_prepare_invoice_line_no_obligation(self):
        contract = self._make_contract(
            (
                self.product,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                False,
            )
        )
        line = contract.contract_line_ids
        vals = line._prepare_invoice_line()
        self.assertNotIn("perf_obligation_id", vals)

    # ------------------------------------------------------------------
    # P&L account propagation — sale contracts (income)
    # ------------------------------------------------------------------

    def test_income_account_set_from_product(self):
        """The product's income account lands on the obligation when no
        fiscal position mapping overrides it."""
        account = self.env["account.account"].create(
            {
                "name": "Test Revenue Account",
                "code": "TEST.REV.001",
                "account_type": "income",
            }
        )
        self.product.property_account_income_id = account
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.pl_account_id, account)

    def test_income_account_mapped_through_fiscal_position(self):
        """When the contract has a fiscal position with an account mapping
        for the product's income account, the mapped account is used."""
        src_account = self.env["account.account"].create(
            {
                "name": "Revenue Source",
                "code": "TEST.REV.SRC",
                "account_type": "income",
            }
        )
        dst_account = self.env["account.account"].create(
            {
                "name": "Revenue Destination",
                "code": "TEST.REV.DST",
                "account_type": "income",
            }
        )
        self.product.property_account_income_id = src_account
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Test FPos",
                "account_ids": [
                    Command.create(
                        {
                            "account_src_id": src_account.id,
                            "account_dest_id": dst_account.id,
                        }
                    )
                ],
            }
        )
        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract FPos",
                "partner_id": self.partner.id,
                "contract_type": "sale",
                "fiscal_position_id": fiscal_position.id,
                "line_recurrence": True,
            }
        )
        self.env["contract.line"].create(
            {
                "contract_id": contract.id,
                "product_id": self.product.id,
                "name": self.product.name,
                "quantity": 1,
                "price_unit": 1200.0,
                "date_start": fields.Date.from_string("2026-01-01"),
                "date_end": fields.Date.from_string("2026-12-31"),
                "recurring_next_date": fields.Date.from_string("2026-01-01"),
                "recurring_interval": 1,
                "recurring_rule_type": "monthly",
                "recurring_invoicing_type": "pre-paid",
                "uom_id": self.product.uom_id.id,
                "perf_obligation_auto_create": True,
            }
        )
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.pl_account_id, dst_account)

    def test_income_account_not_set_when_product_has_none(self):
        """If the product has no income account, pl_account_id is not set."""
        self.product.property_account_income_id = False
        contract = self._make_contract(
            (
                self.product,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertFalse(po.pl_account_id)

    def test_income_account_no_mapping_falls_back_to_product_account(self):
        """A fiscal position without a mapping for the product account leaves
        the product's account unchanged on the obligation."""
        account = self.env["account.account"].create(
            {
                "name": "Revenue Unmapped",
                "code": "TEST.REV.UNMAP",
                "account_type": "income",
            }
        )
        self.product.property_account_income_id = account
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Empty FPos",
            }
        )
        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract Empty FPos",
                "partner_id": self.partner.id,
                "contract_type": "sale",
                "fiscal_position_id": fiscal_position.id,
                "line_recurrence": True,
            }
        )
        self.env["contract.line"].create(
            {
                "contract_id": contract.id,
                "product_id": self.product.id,
                "name": self.product.name,
                "quantity": 1,
                "price_unit": 1200.0,
                "date_start": fields.Date.from_string("2026-01-01"),
                "date_end": fields.Date.from_string("2026-12-31"),
                "recurring_next_date": fields.Date.from_string("2026-01-01"),
                "recurring_interval": 1,
                "recurring_rule_type": "monthly",
                "recurring_invoicing_type": "pre-paid",
                "uom_id": self.product.uom_id.id,
                "perf_obligation_auto_create": True,
            }
        )
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.pl_account_id, account)

    # ------------------------------------------------------------------
    # P&L account propagation — purchase contracts (expense)
    # ------------------------------------------------------------------

    def test_expense_account_set_from_product_on_purchase_contract(self):
        """The product's expense account lands on the obligation for
        purchase contracts."""
        account = self.env["account.account"].create(
            {
                "name": "Test Expense Account",
                "code": "TEST.EXP.001",
                "account_type": "expense",
            }
        )
        self.product.property_account_expense_id = account
        contract = self._make_purchase_contract_line(self.product)
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.pl_account_id, account)

    def test_expense_account_mapped_through_fiscal_position_on_purchase_contract(self):
        """Fiscal position mapping is applied to the expense account on
        purchase contracts."""
        src_account = self.env["account.account"].create(
            {
                "name": "Expense Source",
                "code": "TEST.EXP.SRC",
                "account_type": "expense",
            }
        )
        dst_account = self.env["account.account"].create(
            {
                "name": "Expense Destination",
                "code": "TEST.EXP.DST",
                "account_type": "expense",
            }
        )
        self.product.property_account_expense_id = src_account
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Purchase FPos",
                "account_ids": [
                    Command.create(
                        {
                            "account_src_id": src_account.id,
                            "account_dest_id": dst_account.id,
                        }
                    )
                ],
            }
        )
        contract = self.env["contract.contract"].create(
            {
                "name": "Purchase Contract FPos",
                "partner_id": self.partner.id,
                "contract_type": "purchase",
                "fiscal_position_id": fiscal_position.id,
                "line_recurrence": True,
            }
        )
        self.env["contract.line"].create(
            {
                "contract_id": contract.id,
                "product_id": self.product.id,
                "name": self.product.name,
                "quantity": 1,
                "price_unit": 1200.0,
                "date_start": fields.Date.from_string("2026-01-01"),
                "date_end": fields.Date.from_string("2026-12-31"),
                "recurring_next_date": fields.Date.from_string("2026-01-01"),
                "recurring_interval": 1,
                "recurring_rule_type": "monthly",
                "recurring_invoicing_type": "pre-paid",
                "uom_id": self.product.uom_id.id,
                "perf_obligation_auto_create": True,
            }
        )
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.pl_account_id, dst_account)

    def test_expense_account_not_set_when_product_has_none(self):
        """If the product has no expense account, pl_account_id is not set
        on purchase contract obligations."""
        self.product.property_account_expense_id = False
        contract = self._make_purchase_contract_line(self.product)
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertFalse(po.pl_account_id)

    def test_purchase_contract_uses_expense_account_not_income(self):
        """Purchase contracts use property_account_expense_id, not
        property_account_income_id."""
        income_account = self.env["account.account"].create(
            {
                "name": "Revenue",
                "code": "TEST.REV.PURCH",
                "account_type": "income",
            }
        )
        expense_account = self.env["account.account"].create(
            {
                "name": "Expense",
                "code": "TEST.EXP.PURCH",
                "account_type": "expense",
            }
        )
        self.product.property_account_income_id = income_account
        self.product.property_account_expense_id = expense_account
        contract = self._make_purchase_contract_line(self.product)
        po = contract.contract_line_ids.perf_obligation_ids
        self.assertEqual(po.pl_account_id, expense_account)
        self.assertNotEqual(po.pl_account_id, income_account)
