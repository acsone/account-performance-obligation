# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
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
        cls.product_contract = cls.env["product.product"].create(
            {
                "name": "Contract Product",
                "type": "service",
                "is_contract": True,
                "perf_obligation_auto_create": True,
                "perf_obligation_recognition_method": "contract",
                "recurring_interval": 1,
                "recurring_rule_type": "monthly",
                "recurring_invoicing_type": "pre-paid",
                "recurrence_number": 12,
                "recurrence_interval": "yearly",
                "property_contract_template_id": cls.contract_template.id,
            }
        )
        cls.product_plain = cls.env["product.product"].create(
            {
                "name": "Plain Contract Product",
                "type": "service",
                "is_contract": True,
            }
        )

    def _make_contract(self, *lines):
        """Build a contract with lines. Each line is (product, qty, price_unit,
        date_start, date_end)."""
        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": self.partner.id,
                "contract_type": "sale",
                "line_recurrence": True,
            }
        )
        for product, qty, price, date_start, date_end in lines:
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
                }
            )
        return contract

    def test_contract_method_creates_obligation(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
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
                self.product_contract,
                3,
                400.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        po = contract.contract_line_ids.perf_obligation_ids
        # _get_quantity_to_invoice returns self.quantity = 3
        self.assertEqual(po.total_amount, 3 * 400.0)

    def test_plain_product_no_obligation(self):
        contract = self._make_contract(
            (
                self.product_plain,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        self.assertFalse(contract.contract_line_ids.perf_obligation_ids)

    def test_obligation_linked_to_contract_line(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        line = contract.contract_line_ids
        self.assertEqual(line.perf_obligation_ids.contract_line_id, line)

    def test_duplicate_guard(self):
        """Calling _create_perf_obligation_if_needed again updates the existing
        obligation instead of creating a duplicate."""
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        line = contract.contract_line_ids
        line._create_perf_obligation_if_needed()
        self.assertEqual(len(line.perf_obligation_ids), 1)

    def test_perf_obligation_count(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            ),
            (
                self.product_contract,
                1,
                800.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-06-30"),
            ),
        )
        self.assertEqual(contract.perf_obligation_count, 2)

    def test_perf_obligation_count_excludes_plain_lines(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            ),
            (
                self.product_plain,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            ),
        )
        self.assertEqual(contract.perf_obligation_count, 1)

    def test_cancel_sets_total_amount_to_zero_when_nothing_invoiced(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
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
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
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
                self.product_plain,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        line = contract.contract_line_ids
        line.write({"is_canceled": True})  # must not raise

    def test_unlink_deletes_obligation(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
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
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
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
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
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

    def test_prepare_invoice_line_carries_obligation(self):
        contract = self._make_contract(
            (
                self.product_contract,
                1,
                1200.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        line = contract.contract_line_ids
        vals = line._prepare_invoice_line()
        self.assertEqual(vals.get("perf_obligation_id"), line.perf_obligation_ids[0].id)

    def test_prepare_invoice_line_no_obligation(self):
        contract = self._make_contract(
            (
                self.product_plain,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
            )
        )
        line = contract.contract_line_ids
        vals = line._prepare_invoice_line()
        self.assertNotIn("perf_obligation_id", vals)

    def test_contract_method_requires_is_contract(self):
        """Recognition method 'contract' cannot be set on a non-contract product."""
        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            self.env["product.template"].create(
                {
                    "name": "Non-contract product",
                    "type": "service",
                    "is_contract": False,
                    "perf_obligation_recognition_method": "contract",
                }
            )

    def test_create_contract_line_from_sol_reuses_obligation(self):
        """Creating a contract line from a SOL links the existing performance obligation
        to the contract line instead of creating a new one."""
        # Setup: confirm a sale order with a contract product
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_contract.id,
                            "product_uom_qty": 1,
                            "price_unit": 1200.0,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        sol = order.order_line
        po = sol.perf_obligation_ids
        self.assertEqual(len(po), 1)

        # Create contract and contract line from SOL
        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": self.partner.id,
                "contract_type": "sale",
                "line_recurrence": True,
            }
        )
        sol.create_contract_line(contract)
        contract_line = contract.contract_line_ids

        # Same performance obligation, no duplicate
        self.assertEqual(len(contract_line.perf_obligation_ids), 1)
        self.assertEqual(contract_line.perf_obligation_ids, po)

    def test_create_contract_line_from_sol_updates_obligation_dates(self):
        """The performance obligation dates are updated to match the contract line
        dates."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_contract.id,
                            "product_uom_qty": 1,
                            "price_unit": 1200.0,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        sol = order.order_line
        po = sol.perf_obligation_ids

        contract = self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": self.partner.id,
                "contract_type": "sale",
                "line_recurrence": True,
            }
        )
        sol.create_contract_line(contract)
        contract_line = contract.contract_line_ids

        self.assertEqual(po.start_date, contract_line.date_start)
        self.assertEqual(po.end_date, contract_line.date_end)
