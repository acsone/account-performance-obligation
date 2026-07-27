# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models, tools


class PerfObligationScheduleIncome(models.Model):
    _name = "perf.obligation.schedule.income"
    _description = "Performance Obligation Recognition Schedule (Income)"
    _auto = False
    # Must be id because order has importance
    _order = "id"

    perf_obligation_id = fields.Many2one(
        comodel_name="perf.obligation",
        string="Performance Obligation",
        readonly=True,
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Journal Entry",
        readonly=True,
    )
    date = fields.Date(
        readonly=True,
    )
    state = fields.Selection(
        selection=[("draft", "Draft"), ("posted", "Posted")],
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

    def _select(self):
        return """
            ROW_NUMBER() OVER (
                ORDER BY aml.perf_obligation_id, aml.date, aml.move_id
            ) AS id,
            aml.perf_obligation_id,
            aml.move_id,
            aml.date,
            aml.parent_state AS state,
            rc.currency_id,
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
                ORDER BY aml.date, aml.move_id
            ) AS total_recognized_amount,
            SUM(SUM(
                CASE WHEN aa.account_type IN (
                    'asset_current', 'liability_current'
                )
                THEN aml.balance ELSE 0 END
            )) OVER (
                PARTITION BY aml.perf_obligation_id
                ORDER BY aml.date, aml.move_id
            ) AS total_deferred_accrued_amount,
            -SUM(SUM(
                CASE WHEN aa.account_type LIKE 'income%%'
                THEN aml.balance ELSE 0 END
            )) OVER (
                PARTITION BY aml.perf_obligation_id
                ORDER BY aml.date, aml.move_id
            )
            - SUM(SUM(
                CASE WHEN aa.account_type IN (
                    'asset_current', 'liability_current'
                )
                THEN aml.balance ELSE 0 END
            )) OVER (
                PARTITION BY aml.perf_obligation_id
                ORDER BY aml.date, aml.move_id
            ) AS total_invoiced_amount
        """

    def _from(self):
        return """
            account_move_line aml
            JOIN account_account aa ON aa.id = aml.account_id
            JOIN perf_obligation po ON po.id = aml.perf_obligation_id
            JOIN res_company rc ON rc.id = po.company_id
        """

    def _where(self):
        return """
            aml.parent_state IN ('draft', 'posted')
            AND po.perf_type = 'income'
        """

    def _group_by(self):
        return """
            aml.perf_obligation_id,
            aml.move_id,
            aml.date,
            aml.parent_state,
            rc.currency_id
        """

    def _query(self):
        return f"""
            SELECT
                {self._select()}
            FROM
                {self._from()}
            WHERE
                {self._where()}
            GROUP BY
                {self._group_by()}
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"CREATE OR REPLACE VIEW {self._table} AS ({self._query()})"
        )
