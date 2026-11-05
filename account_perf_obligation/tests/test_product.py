# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).


from odoo.addons.account_perf_obligation.tests.common import PerfObligationCommon


class TestPerfObligationProduct(PerfObligationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({"name": "Test Product"})
        cls.other_product = cls.env["product.product"].create(
            {"name": "Other Test Product"}
        )

    def test_product_set_on_pl_line_only_income(self):
        po = self._create_obligation(perf_type="income", total_amount=300.0)
        po.product_id = self.product
        move = po._recognize(100, "2026-01-31", "Jan")
        pl_line = move.line_ids.filtered(lambda line: line.account_id == self.inc_pl)
        bs_lines = move.line_ids - pl_line
        self.assertEqual(pl_line.product_id, self.product)
        self.assertTrue(bs_lines)
        self.assertFalse(bs_lines.product_id)

    def test_product_set_on_pl_line_only_expense(self):
        po = self._create_obligation(perf_type="expense", total_amount=300.0)
        po.product_id = self.product
        move = po._recognize(100, "2026-01-31", "Jan")
        pl_line = move.line_ids.filtered(lambda line: line.account_id == self.exp_pl)
        bs_lines = move.line_ids - pl_line
        self.assertEqual(pl_line.product_id, self.product)
        self.assertTrue(bs_lines)
        self.assertFalse(bs_lines.product_id)

    def test_no_product_set_means_no_product_on_lines(self):
        po = self._create_obligation(perf_type="income", total_amount=300.0)
        self.assertFalse(po.product_id)
        move = po._recognize(100, "2026-01-31", "Jan")
        self.assertFalse(move.line_ids.mapped("product_id"))
