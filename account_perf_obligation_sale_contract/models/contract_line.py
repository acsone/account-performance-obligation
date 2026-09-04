# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class ContractLine(models.Model):
    _inherit = "contract.line"

    @api.onchange("product_id")
    def onchange_product_id_auto_create_perf_obligation(self):
        for contract_line in self:
            contract_line.perf_obligation_auto_create = (
                contract_line.product_id.perf_obligation_sale_auto_create
            )
