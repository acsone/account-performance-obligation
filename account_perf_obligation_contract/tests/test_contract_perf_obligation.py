# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import ValidationError
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
        """Build a contract with lines. Each line is (product, qty, price_unit,
        date_start, date_end, autocreate)."""
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
        self.assertTrue(line.perf_obligation_id)
        po = line.perf_obligation_id
        self.assertEqual(po.perf_type, "income")
        self.assertEqual(po.start_date, fields.Date.from_string("2026-01-01"))
        self.assertEqual(po.end_date, fields.Date.from_string("2026-12-31"))
        self.assertEqual(po.recognition_at_date_method, "daily")

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
        po = contract.contract_line_ids.perf_obligation_id
        # _get_quantity_to_invoice returns self.quantity = 3
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
        self.assertFalse(contract.contract_line_ids.perf_obligation_id)

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
        self.assertEqual(line.perf_obligation_id.id, line.perf_obligation_id.id)
        self.assertTrue(line.perf_obligation_id)

    def test_duplicate_guard(self):
        """Calling _create_or_update_perf_obligation again updates the existing
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
        po_id = line.perf_obligation_id.id
        line._create_or_update_perf_obligation()
        self.assertEqual(line.perf_obligation_id.id, po_id)

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
        po = line.perf_obligation_id
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
        po = line.perf_obligation_id
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

    def test_cancel_sets_total_amount_to_invoiced_amount(self):
        """When some invoices are posted, cancellation clamps total_amount to
        the already-invoiced sum rather than zeroing it out."""
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
        po = line.perf_obligation_id
        # Generate and post an invoice for 3 months worth
        invoice = contract._recurring_create_invoice()
        invoice.action_post()
        # Simulate a second posted invoice
        invoice2 = contract._recurring_create_invoice()
        invoice2.action_post()
        invoiced = line._get_perf_obligation_invoiced_amount()
        self.assertGreater(invoiced, 0.0)
        line.write({"is_canceled": True})
        self.assertAlmostEqual(po.total_amount, invoiced)

    def test_cancel_with_refund_reduces_invoiced_amount(self):
        """A posted credit note reduces the effective invoiced amount used when
        clamping on cancellation."""
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
        invoice = contract._recurring_create_invoice()
        invoice.action_post()
        invoiced_before_refund = line._get_perf_obligation_invoiced_amount()
        # Reverse the invoice (creates a posted credit note)
        refund = invoice._reverse_moves(
            default_values_list=[{"invoice_date": invoice.invoice_date}]
        )
        refund.action_post()
        invoiced_after_refund = line._get_perf_obligation_invoiced_amount()
        self.assertEqual(invoiced_after_refund, 0.0)
        self.assertLess(invoiced_after_refund, invoiced_before_refund)

    def test_invoiced_amount_only_counts_posted_moves(self):
        """Draft invoices must not be counted toward the invoiced amount."""
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
        contract._recurring_create_invoice()  # left in draft
        self.assertEqual(line._get_perf_obligation_invoiced_amount(), 0.0)

    def test_invoiced_amount_scoped_to_perf_obligation(self):
        """Move lines linked to a different perf obligation are excluded from
        the invoiced amount calculation."""
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
        invoice = contract._recurring_create_invoice()
        invoice.action_post()
        # Detach the obligation from the invoice line to simulate a line
        # belonging to a different obligation
        invoice.invoice_line_ids.write({"perf_obligation_id": False})
        self.assertEqual(line._get_perf_obligation_invoiced_amount(), 0.0)

    def test_cancel_purchase_contract_uses_in_invoice(self):
        """Cancellation on a purchase contract reads in_invoice/in_refund moves,
        not out_invoice ones."""
        contract = self._make_contract(
            (
                self.product,
                1,
                600.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            ),
            contract_type="purchase",
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_id
        self.assertEqual(po.total_amount, 600.0)
        # No vendor bills posted → cancellation should zero out the obligation
        line.write({"is_canceled": True})
        self.assertEqual(po.total_amount, 0.0)

    def test_negative_invoiced_amount_raises(self):
        """A net negative invoiced amount (refunds > invoices) must raise rather
        than silently clamp to zero."""
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
        invoice = contract._recurring_create_invoice()
        invoice.action_post()
        refund = invoice._reverse_moves(
            default_values_list=[{"invoice_date": invoice.invoice_date}]
        )
        refund.action_post()
        # Manually push a second refund to make net go negative
        refund2 = invoice._reverse_moves(
            default_values_list=[{"invoice_date": invoice.invoice_date}]
        )
        refund2.action_post()
        with self.assertRaises(ValidationError):
            line._get_perf_obligation_invoiced_amount()

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
        po = line.perf_obligation_id
        po_id = po.id
        line.unlink()
        self.assertFalse(self.env["perf.obligation"].browse(po_id).exists())

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
        self.assertEqual(vals.get("perf_obligation_id"), line.perf_obligation_id.id)

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

    def test_update_obligation_raises_when_multiple_sources(self):
        """_update_perf_obligation raises ValidationError when the obligation
        is shared by more than one source record (e.g. manually assigned to a
        second contract line), because automatic sync would be ambiguous."""
        contract = self._make_contract(
            (
                self.product,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        line = contract.contract_line_ids
        po = line.perf_obligation_id
        # Create a second contract and manually point its line at the
        # same obligation
        contract2 = self._make_contract(
            (
                self.product,
                1,
                500.0,
                fields.Date.from_string("2026-01-01"),
                fields.Date.from_string("2026-12-31"),
                True,
            )
        )
        second_line = contract2.contract_line_ids
        second_line.perf_obligation_id = po
        # Now _get_sources() returns both lines, so the guard must fire.
        with self.assertRaisesRegex(
            ValidationError, "originates from multiple sources"
        ) as e:
            line._update_perf_obligation(po)
        self.assertIn(line.display_name, e.exception.args[0])
        self.assertIn(second_line.display_name, e.exception.args[0])
