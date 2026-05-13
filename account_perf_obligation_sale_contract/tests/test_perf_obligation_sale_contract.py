# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestPerfObligationSaleContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Customer"})
        cls.contract_template = cls.env["contract.template"].create(
            {"name": "Test Contract Template"}
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "At Once Product",
                "type": "service",
                "is_contract": True,
                "perf_obligation_sale_auto_create": True,
                "perf_obligation_sale_recognition_method": "at_once",
                "property_contract_template_id": cls.contract_template.id,
            }
        )

    def _make_order(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1,
                            "price_unit": 1200.0,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        return order

    def _make_contract(self):
        return self.env["contract.contract"].create(
            {
                "name": "Test Contract",
                "partner_id": self.partner.id,
                "contract_type": "sale",
            }
        )

    def test_create_contract_line_from_sol_reuses_obligation(self):
        """Creating a contract line from a SOL links the existing performance
        obligation to the contract line instead of creating a new one."""
        order = self._make_order()
        sol = order.order_line
        po = sol.perf_obligation_ids
        self.assertEqual(len(po), 1)
        contract = self._make_contract()
        sol.create_contract_line(contract)
        contract_line = contract.contract_line_ids
        # Same PO, no duplicate
        self.assertEqual(len(contract_line.perf_obligation_ids), 1)
        self.assertEqual(contract_line.perf_obligation_ids, po)

    def test_create_contract_line_from_sol_updates_obligation_dates(self):
        """The performance obligation dates are updated to match the contract
        line dates."""
        order = self._make_order()
        sol = order.order_line
        po = sol.perf_obligation_ids
        contract = self._make_contract()
        sol.create_contract_line(contract)
        contract_line = contract.contract_line_ids
        self.assertEqual(po.start_date, contract_line.date_start)
        self.assertEqual(po.end_date, contract_line.date_end)
