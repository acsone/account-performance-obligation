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
        cls.product_days = cls.env["product.product"].create(
            {
                "name": "10-Day Product",
                "type": "service",
                "perf_obligation_auto_create": True,
                "perf_obligation_recognition_method": "days",
                "perf_obligation_days_duration": 10,
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

    def test_days_creates_obligation(self):
        order = self._make_order((self.product_days, 1, 800.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        conf = order.date_order.date()
        self.assertEqual(len(po), 1)
        self.assertEqual(po.perf_type, "income")
        self.assertEqual(po.total_amount, 800.0)
        self.assertEqual(po.start_date, conf)
        self.assertEqual(po.end_date, conf + relativedelta(days=10))
        self.assertEqual(po.recognition_at_date_method, "daily")

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
        """Re-calling _create_perf_obligation_if_needed updates the existing
        obligation instead of creating a duplicate."""
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

    def test_cancel_sets_total_amount_to_invoiced(self):
        """On cancellation with nothing invoiced, total_amount is set to 0."""
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        self.assertEqual(po.total_amount, 1000.0)
        order.action_cancel()
        self.assertEqual(po.total_amount, 0.0)

    def test_cancel_sets_total_amount_on_all_lines(self):
        """Cancellation freezes all obligations at their invoiced amount."""
        order = self._make_order(
            (self.product_at_once, 1, 1000.0),
            (self.product_months, 1, 1200.0),
        )
        order.action_confirm()
        order.action_cancel()
        for po in order.order_line.mapped("perf_obligation_ids"):
            self.assertEqual(po.total_amount, 0.0)

    def test_cancel_without_obligations_no_error(self):
        order = self._make_order((self.product_plain, 1, 500.0))
        order.action_confirm()
        order.action_cancel()  # must not raise

    # ------------------------------------------------------------------
    # Re-confirmation updates existing obligations
    # ------------------------------------------------------------------

    def test_reconfirm_updates_obligation_amount(self):
        """Re-confirming a cancelled order updates the existing ODP's
        total_amount to match the current line subtotal."""
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        line = order.order_line
        po = line.perf_obligation_ids
        self.assertEqual(po.total_amount, 1000.0)

        order.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(po.total_amount, 0.0)

        # Update price before re-confirmation
        line.price_unit = 1500.0
        order.action_draft()
        order.action_confirm()

        # Same ODP, no duplicate
        self.assertEqual(len(line.perf_obligation_ids), 1)
        self.assertEqual(po.total_amount, 1500.0)

    def test_reconfirm_updates_obligation_dates_months(self):
        """Re-confirming recomputes start/end dates from the current
        order confirmation date."""
        order = self._make_order((self.product_months, 1, 1200.0))
        order.action_confirm()
        line = order.order_line
        po = line.perf_obligation_ids
        original_start = po.start_date
        original_end = po.end_date

        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        order.action_confirm()

        conf = order.date_order.date()
        self.assertEqual(len(line.perf_obligation_ids), 1)
        self.assertEqual(po.start_date, conf)
        self.assertEqual(po.end_date, conf + relativedelta(months=3))
        # Dates are recomputed (they should equal the originals in this test
        # since date_order doesn't change, but the write is verified)
        self.assertEqual(po.start_date, original_start)
        self.assertEqual(po.end_date, original_end)

    def test_reconfirm_does_not_create_obligation_for_plain_product(self):
        """Re-confirmation must not create obligations for non-qualifying lines."""
        order = self._make_order((self.product_plain, 1, 500.0))
        order.action_confirm()
        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertFalse(order.order_line.perf_obligation_ids)

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

    # ------------------------------------------------------------------
    # Chatter messages
    # ------------------------------------------------------------------

    def test_cancel_posts_chatter_message(self):
        """Cancellation posts a message on the performance obligation chatter."""
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        invoice = order._create_invoices()
        invoice.action_post()
        msg_count_before = len(po.message_ids)
        order.action_cancel()
        self.assertEqual(len(po.message_ids), msg_count_before + 1)
        self.assertIn("$&nbsp;1,000.00", po.message_ids[0].body)

    def test_reconfirm_posts_chatter_message(self):
        """Re-confirmation posts a message on the performance obligation chatter."""
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        line = order.order_line
        po = line.perf_obligation_ids
        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        msg_count_before = len(po.message_ids)
        order.action_confirm()
        self.assertEqual(len(po.message_ids), msg_count_before + 1)
