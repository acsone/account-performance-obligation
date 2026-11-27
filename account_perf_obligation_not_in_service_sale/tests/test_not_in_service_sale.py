# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class TestSaleNotInService(TransactionCase):
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
        cls.product_no_dates = cls.env["product.product"].create(
            {
                "name": "No Dates Product",
                "type": "service",
                "perf_obligation_sale_auto_create": True,
            }
        )

    def _make_order(self, *lines):
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

    def test_obligation_put_in_service_on_confirmation(self):
        for product in (self.product_at_once, self.product_months, self.product_days):
            with self.subTest(product=product.name):
                order = self._make_order((product, 1, 1000.0))
                order.action_confirm()
                po = order.order_line.perf_obligation_id
                self.assertEqual(po.state, "open")
                self.assertFalse(po.not_in_service)

    def test_obligation_without_method_stays_not_in_service(self):
        order = self._make_order((self.product_no_dates, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_id
        self.assertEqual(po.state, "open")
        self.assertTrue(po.not_in_service)

    def test_obligation_put_in_service_by_non_accounting_user(self):
        order = self._make_order((self.product_at_once, 1, 1000.0))
        salesman = new_test_user(
            self.env,
            login="perf_obligation_nis_salesman",
            groups="sales_team.group_sale_salesman_all_leads",
        )
        order.with_user(salesman).action_confirm()
        self.assertFalse(order.order_line.perf_obligation_id.not_in_service)

    def test_reconfirm_keeps_obligation_in_service(self):
        order = self._make_order((self.product_at_once, 1, 1000.0))
        order.action_confirm()
        po = order.order_line.perf_obligation_id
        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertFalse(po.not_in_service)
