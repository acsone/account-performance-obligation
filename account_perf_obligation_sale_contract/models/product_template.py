# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.constrains(
        "perf_obligation_sale_auto_create",
        "perf_obligation_sale_recognition_method",
        "is_contract",
    )
    def _check_perf_obligation_sale_recognition_method(self):
        """
        When a product is configured both as a contract product and for automatic
        obligation creation, the contract line dates take precedence over recognition
        method so we ignore contract products for the recognition method check.
        """
        non_contract_products = self.filtered(lambda product: not product.is_contract)
        return super(
            ProductTemplate, non_contract_products
        )._check_perf_obligation_sale_recognition_method()
