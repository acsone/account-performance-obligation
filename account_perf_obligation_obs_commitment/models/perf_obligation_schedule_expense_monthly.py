# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class PerfObligationScheduleExpenseMonthly(models.Model):
    _inherit = "perf.obligation.schedule.expense.monthly"

    def _where(self):
        return super()._where() + " AND aa.account_type != 'off_balance'"
