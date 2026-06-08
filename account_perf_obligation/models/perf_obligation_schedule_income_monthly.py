# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models, tools


class PerfObligationScheduleIncomeMonthly(models.Model):
    _name = "perf.obligation.schedule.income.monthly"
    _description = "Performance Obligation Recognition Schedule by Month (Income)"
    _auto = False
    _order = "id"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        readonly=True,
    )
    month = fields.Char(
        readonly=True,
    )
    date = fields.Date(
        readonly=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("posted", "Posted"), ("mixed", "Mixed")],
        string="Status",
        readonly=True,
    )
    recognized_amount = fields.Monetary(
        string="Recognized",
        readonly=True,
        currency_field="currency_id",
    )
    invoiced_amount = fields.Monetary(
        string="Invoiced",
        readonly=True,
        currency_field="currency_id",
    )
    deferred_accrued_amount = fields.Monetary(
        string="Deferred / Accrued",
        readonly=True,
        currency_field="currency_id",
    )
    total_recognized_amount = fields.Monetary(
        string="Total Recognized",
        readonly=True,
        currency_field="currency_id",
    )
    total_deferred_accrued_amount = fields.Monetary(
        string="Total Deferred / Accrued",
        readonly=True,
        currency_field="currency_id",
    )
    total_invoiced_amount = fields.Monetary(
        string="Total Invoiced",
        readonly=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY aml.perf_obligation_id,
                            DATE_TRUNC('month', aml.date)
                    ) AS id,
                    aml.perf_obligation_id,
                    DATE_TRUNC('month', aml.date)::date AS date,
                    TO_CHAR(DATE_TRUNC('month', aml.date), 'YYYY-MM') AS month,
                    rc.currency_id,
                    CASE
                        WHEN bool_and(aml.parent_state = 'posted') THEN 'posted'
                        WHEN bool_and(aml.parent_state = 'draft') THEN 'draft'
                        ELSE 'mixed'
                    END AS state,
                    -SUM(
                        CASE WHEN aa.account_type LIKE 'income%%'
                        THEN aml.balance ELSE 0 END
                    ) AS recognized_amount,
                    -SUM(
                        CASE WHEN aa.account_type LIKE 'income%%'
                        THEN aml.balance ELSE 0 END
                    )
                    - SUM(
                        CASE WHEN aa.account_type IN (
                            'asset_current', 'liability_current'
                        )
                        THEN aml.balance ELSE 0 END
                    ) AS invoiced_amount,
                    SUM(
                        CASE WHEN aa.account_type IN (
                            'asset_current', 'liability_current'
                        )
                        THEN aml.balance ELSE 0 END
                    ) AS deferred_accrued_amount,
                    -SUM(SUM(
                        CASE WHEN aa.account_type LIKE 'income%%'
                        THEN aml.balance ELSE 0 END
                    )) OVER (
                        PARTITION BY aml.perf_obligation_id
                        ORDER BY DATE_TRUNC('month', aml.date)
                    ) AS total_recognized_amount,
                    SUM(SUM(
                        CASE WHEN aa.account_type IN (
                            'asset_current', 'liability_current'
                        )
                        THEN aml.balance ELSE 0 END
                    )) OVER (
                        PARTITION BY aml.perf_obligation_id
                        ORDER BY DATE_TRUNC('month', aml.date)
                    ) AS total_deferred_accrued_amount,
                    -SUM(SUM(
                        CASE WHEN aa.account_type LIKE 'income%%'
                        THEN aml.balance ELSE 0 END
                    )) OVER (
                        PARTITION BY aml.perf_obligation_id
                        ORDER BY DATE_TRUNC('month', aml.date)
                    )
                    - SUM(SUM(
                        CASE WHEN aa.account_type IN (
                            'asset_current', 'liability_current'
                        )
                        THEN aml.balance ELSE 0 END
                    )) OVER (
                        PARTITION BY aml.perf_obligation_id
                        ORDER BY DATE_TRUNC('month', aml.date)
                    ) AS total_invoiced_amount
                FROM account_move_line aml
                JOIN account_account aa ON aa.id = aml.account_id
                JOIN perf_obligation po ON po.id = aml.perf_obligation_id
                JOIN res_company rc ON rc.id = po.company_id
                WHERE aml.parent_state IN ('draft', 'posted')
                  AND po.perf_type = 'income'
                GROUP BY
                    aml.perf_obligation_id,
                    DATE_TRUNC('month', aml.date),
                    rc.currency_id
            )
        """)
