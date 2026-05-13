# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    perf_obligation_sale_auto_create = fields.Boolean(
        string="Auto-create Performance Obligation",
        default=False,
    )
    perf_obligation_sale_recognition_method = fields.Selection(
        selection=[
            ("at_once", "At once"),
            ("months", "Over several months"),
            ("days", "Over several days"),
        ],
        string="Revenue Recognition Duration",
        help="Determines how the start and end dates of the performance "
        "obligation are computed when it is created.",
    )
    perf_obligation_sale_months_duration = fields.Integer(
        string="Recognition Duration (months)",
        help="Number of months over which the performance obligation "
        "is recognized. Used when the recognition method is "
        "'Over several months'.",
    )
    perf_obligation_sale_days_duration = fields.Integer(
        string="Recognition Duration (days)",
        help="Number of days over which the performance obligation "
        "is recognized. Used when the recognition method is "
        "'Over several days'.",
    )

    @api.constrains(
        "perf_obligation_sale_auto_create",
        "perf_obligation_sale_recognition_method",
    )
    def _check_perf_obligation_sale_recognition_method(self):
        for rec in self:
            if (
                rec.perf_obligation_sale_auto_create
                and not rec.perf_obligation_sale_recognition_method
            ):
                raise ValidationError(
                    _(
                        "A recognition duration method is required when "
                        "automatic performance obligation creation is enabled "
                        "on product '%(name)s'.",
                        name=rec.display_name,
                    )
                )

    @api.constrains(
        "perf_obligation_sale_recognition_method",
        "perf_obligation_sale_months_duration",
    )
    def _check_perf_obligation_sale_months_duration(self):
        for rec in self:
            if rec.perf_obligation_sale_recognition_method != "months":
                continue
            if rec.perf_obligation_sale_months_duration <= 0:
                raise ValidationError(
                    _(
                        "The recognition duration must be a strictly "
                        "positive number of months on product '%(name)s'.",
                        name=rec.display_name,
                    )
                )

    @api.constrains(
        "perf_obligation_sale_recognition_method",
        "perf_obligation_sale_days_duration",
    )
    def _check_perf_obligation_sale_days_duration(self):
        for rec in self:
            if rec.perf_obligation_sale_recognition_method != "days":
                continue
            if rec.perf_obligation_sale_days_duration <= 0:
                raise ValidationError(
                    _(
                        "The recognition duration must be a strictly "
                        "positive number of days on product '%(name)s'.",
                        name=rec.display_name,
                    )
                )
