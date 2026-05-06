# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests.common import TransactionCase


class TestSalePerfObligation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})

        cls.product_at_once = cls.env["product.product"].create(
            {
                "name": "At Once Product",
                "type": "service",
                "perf_obligation_auto_create": True,
                "perf_obligation_recognition_method": "at_once",
            }
        )
        cls.product_months = cls.env["product.product"].create(
            {
                "name": "3-Month Product",
                "type": "service",
                "perf_obligation_auto_create": True,
                "perf_obligation_recognition_method": "months",
                "perf_obligation_months_duration": 3,
            }
        )
        cls.product_plain = cls.env["product.product"].create(
            {
                "name": "Plain Product",
                "type": "service",
            }
        )

    def _make_order(self, *lines):
        """Build a draft sale order. Each line is (product, qty, price_unit)."""
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": p.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                        }
                    )
                    for p, qty, price in lines
                ],
            }
        )

    # ------------------------------------------------------------------
    # Obligation creation on confirm
    # ------------------------------------------------------------------

    def test_at_once_creates_obligation(self):
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        conf = order.date_order.date()
        self.assertEqual(len(po), 1)
        self.assertEqual(po.perf_type, "income")
        self.assertEqual(po.total_amount, 1000.0)
        self.assertEqual(po.start_date, conf)
        self.assertEqual(po.end_date, conf)
        self.assertEqual(po.recognition_at_date_method, "daily")

    def test_months_creates_obligation(self):
        order = self._make_order((self.product_months, 1, 1200.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        conf = order.date_order.date()
        self.assertEqual(len(po), 1)
        self.assertEqual(po.start_date, conf)
        self.assertEqual(po.end_date, conf + relativedelta(months=3))
        self.assertEqual(po.total_amount, 1200.0)

    def test_plain_product_no_obligation(self):
        order = self._make_order((self.product_plain, 1, 500.0))
        order.action_confirm()
        self.assertFalse(order.order_line.perf_obligation_ids)

    def test_mixed_lines_only_qualifying_get_obligation(self):
        order = self._make_order(
            (self.product_at_once, 1, 1000.0),
            (self.product_plain, 1, 500.0),
        )
        order.action_confirm()
        at_once_line = order.order_line.filtered(
            lambda line: line.product_id == self.product_at_once
        )
        plain_line = order.order_line.filtered(
            lambda line: line.product_id == self.product_plain
        )
        self.assertEqual(len(at_once_line.perf_obligation_ids), 1)
        self.assertFalse(plain_line.perf_obligation_ids)

    def test_obligation_linked_to_sale_line(self):
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        line = order.order_line
        self.assertEqual(line.perf_obligation_ids.sale_order_line_id, line)

    def test_duplicate_guard(self):
        """Re-calling _create_perf_obligation_if_needed never creates a duplicate."""
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        line = order.order_line
        line._create_perf_obligation_if_needed()
        self.assertEqual(len(line.perf_obligation_ids), 1)

    # ------------------------------------------------------------------
    # Smart button count
    # ------------------------------------------------------------------

    def test_perf_obligation_count(self):
        order = self._make_order(
            (self.product_at_once, 1, 1000.0),
            (self.product_months, 1, 1200.0),
        )
        self.assertEqual(order.perf_obligation_count, 0)
        order.action_confirm()
        self.assertEqual(order.perf_obligation_count, 2)

    # ------------------------------------------------------------------
    # Cancellation
    # ------------------------------------------------------------------

    def test_cancel_caps_obligation_at_zero(self):
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        self.assertFalse(po.recognition_cap_enabled)
        order.action_cancel()
        self.assertTrue(po.recognition_cap_enabled)
        self.assertEqual(po.recognition_cap_amount, 0.0)

    def test_cancel_caps_all_lines(self):
        order = self._make_order(
            (self.product_at_once, 1, 1000.0),
            (self.product_months, 1, 1200.0),
        )
        order.action_confirm()
        order.action_cancel()
        for po in order.order_line.mapped("perf_obligation_ids"):
            self.assertTrue(po.recognition_cap_enabled)
            self.assertEqual(po.recognition_cap_amount, 0.0)

    def test_cancel_without_obligations_no_error(self):
        order = self._make_order((self.product_plain, 1, 500.0))
        order.action_confirm()
        order.action_cancel()  # must not raise

    # ------------------------------------------------------------------
    # Invoice line propagation
    # ------------------------------------------------------------------

    def test_prepare_invoice_line_carries_obligation(self):
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        line = order.order_line
        vals = line._prepare_invoice_line()
        self.assertEqual(vals.get("perf_obligation_id"), line.perf_obligation_ids[0].id)

    def test_prepare_invoice_line_no_obligation(self):
        order = self._make_order((self.product_plain, 1, 500.0))
        order.action_confirm()
        vals = order.order_line._prepare_invoice_line()
        self.assertNotIn("perf_obligation_id", vals)
