# Copyright 2026 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    perf_obligation_recognition_method = fields.Selection(
        selection_add=[("contract", "Based on contract dates")],
    )

    @api.constrains("perf_obligation_recognition_method", "is_contract")
    def _check_contract_recognition_method(self):
        for record in self:
            if (
                record.perf_obligation_recognition_method == "contract"
                and not record.is_contract
            ):
                raise ValidationError(
                    _(
                        "The recognition method 'Based on contract dates' "
                        "is only available for contract products "
                        "(product '%(name)s').",
                        name=record.display_name,
                    )
                )

    @api.onchange("is_contract", "perf_obligation_recognition_method")
    def _onchange_is_contract_recognition_method(self):
        if (
            not self.is_contract
            and self.perf_obligation_recognition_method == "contract"
        ):
            self.perf_obligation_recognition_method = False
