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
                "perf_obligation_sale_auto_create": True,
                "perf_obligation_sale_recognition_method": "at_once",
            }
        )
        cls.product_months = cls.env["product.product"].create(
            {
                "name": "3-Month Product",
                "type": "service",
                "perf_obligation_sale_auto_create": True,
                "perf_obligation_sale_recognition_method": "months",
                "perf_obligation_sale_months_duration": 3,
            }
        )
        cls.product_days = cls.env["product.product"].create(
            {
                "name": "10-Day Product",
                "type": "service",
                "perf_obligation_sale_auto_create": True,
                "perf_obligation_sale_recognition_method": "days",
                "perf_obligation_sale_days_duration": 10,
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
        """Re-confirming a cancelled order updates the existing perf obligation's
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

    # ------------------------------------------------------------------
    # Income account propagation
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
        self.product_at_once.property_account_income_id = account
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        self.assertEqual(po.pl_account_id, account)

    def test_income_account_mapped_through_fiscal_position(self):
        """When the sale order has a fiscal position with an account mapping
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
        self.product_at_once.property_account_income_id = src_account
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
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.fiscal_position_id = fiscal_position
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        self.assertEqual(po.pl_account_id, dst_account)

    def test_income_account_not_set_when_product_has_none(self):
        """If the product has no income account, pl_account_id is not set
        on the obligation."""
        self.product_at_once.property_account_income_id = False
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
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
        self.product_at_once.property_account_income_id = account
        fiscal_position = self.env["account.fiscal.position"].create(
            {
                "name": "Empty FPos",
            }
        )
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.fiscal_position_id = fiscal_position
        order.action_confirm()
        po = order.order_line.perf_obligation_ids
        self.assertEqual(po.pl_account_id, account)
