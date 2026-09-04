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
        po = sol.perf_obligation_id
        self.assertEqual(len(po), 1)
        contract = self._make_contract()
        sol.create_contract_line(contract)
        contract_line = contract.contract_line_ids
        # Same PO, no duplicate
        self.assertEqual(contract_line.perf_obligation_id, po)

    def test_create_contract_line_from_sol_updates_obligation_dates(self):
        """The performance obligation dates are updated to match the contract
        line dates."""
        order = self._make_order()
        sol = order.order_line
        po = sol.perf_obligation_id
        contract = self._make_contract()
        sol.create_contract_line(contract)
        contract_line = contract.contract_line_ids
        self.assertEqual(po.start_date, contract_line.date_start)
        self.assertEqual(po.end_date, contract_line.date_end)

    def test_contract_product_does_not_require_recognition_method(self):
        """A contract product with auto-create enabled should not require
        a recognition method, since dates come from the contract line."""
        self.env["product.product"].create(
            {
                "name": "Contract Product No Method",
                "type": "service",
                "is_contract": True,
                "perf_obligation_sale_auto_create": True,
                "perf_obligation_sale_recognition_method": False,
                "property_contract_template_id": self.contract_template.id,
            }
        )

    def test_switching_to_contract_clears_constraint(self):
        """Toggling is_contract to True on an existing non-contract product
        that has auto-create enabled should not raise, even without a method."""
        product = self.env["product.product"].create(
            {
                "name": "Switching Product",
                "type": "service",
                "is_contract": False,
                "perf_obligation_sale_auto_create": True,
                "perf_obligation_sale_recognition_method": "at_once",
                "property_contract_template_id": self.contract_template.id,
            }
        )
        # Should not raise when switching to contract, even if method is cleared
        product.write(
            {
                "is_contract": True,
                "perf_obligation_sale_recognition_method": False,
            }
        )

    def test_prepare_contract_line_vals_sets_auto_create_from_product(self):
        """perf_obligation_auto_create is set in contract line vals when the
        product has perf_obligation_sale_auto_create enabled, even if no PO
        exists yet on the SOL."""
        order = self._make_order()
        sol = order.order_line
        # Clear any PO that may have been created on confirm
        sol.perf_obligation_id = False
        contract = self._make_contract()
        vals = sol._prepare_contract_line_values(contract)
        self.assertTrue(vals.get("perf_obligation_auto_create"))

    def test_prepare_contract_line_vals_transfers_existing_obligation(self):
        """When the SOL already has a PO, it is moved to the contract line
        vals and unlinked from the SOL."""
        order = self._make_order()
        sol = order.order_line
        po = sol.perf_obligation_id
        self.assertTrue(po)
        contract = self._make_contract()
        vals = sol._prepare_contract_line_values(contract)
        self.assertEqual(vals.get("perf_obligation_id"), po.id)
        self.assertFalse(sol.perf_obligation_id)

    def test_prepare_contract_line_vals_auto_create_from_existing_obligation(self):
        """perf_obligation_auto_create is also set when the SOL has a PO,
        regardless of the product flag."""
        order = self._make_order()
        sol = order.order_line
        self.assertTrue(sol.perf_obligation_id)
        contract = self._make_contract()
        vals = sol._prepare_contract_line_values(contract)
        self.assertTrue(vals.get("perf_obligation_auto_create"))

    def test_prepare_contract_line_vals_no_auto_create_without_flags(self):
        """perf_obligation_auto_create is not set when the product has no
        auto-create flag and the SOL has no existing PO."""
        product_no_obligation = self.env["product.product"].create(
            {
                "name": "Plain Contract Product",
                "type": "service",
                "is_contract": True,
                "perf_obligation_sale_auto_create": False,
                "property_contract_template_id": self.contract_template.id,
            }
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product_no_obligation.id,
                            "product_uom_qty": 1,
                            "price_unit": 100.0,
                        },
                    )
                ],
            }
        )
        order.action_confirm()
        sol = order.order_line
        self.assertFalse(sol.perf_obligation_id)
        contract = self._make_contract()
        vals = sol._prepare_contract_line_values(contract)
        self.assertFalse(vals.get("perf_obligation_auto_create"))
        self.assertNotIn("perf_obligation_id", vals)
