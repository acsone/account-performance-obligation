# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from .common import PerfObligationCommon


class TestPerfObligationAnalyticDistribution(PerfObligationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Perf Obligation Plan"}
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Perf Obligation Analytic Account",
                "plan_id": cls.analytic_plan.id,
                "company_id": False,
            }
        )

    def _distribution(self):
        return {str(self.analytic_account.id): 100.0}

    def test_distribution_set_on_pl_line_only(self):
        """An analytic item on the balance sheet counterpart would carry the
        opposite amount and cancel the P&L one out."""
        po = self._create_obligation(perf_type="income", total_amount=300.0)
        po.analytic_distribution = self._distribution()
        move = po._recognize(100, "2026-01-31", "Jan")
        pl_line = move.line_ids.filtered(lambda line: line.account_id == self.inc_pl)
        bs_line = move.line_ids.filtered(
            lambda line: line.account_id == self.inc_debit_bs
        )
        self.assertEqual(pl_line.analytic_distribution, self._distribution())
        self.assertFalse(bs_line.analytic_distribution)

    def test_no_distribution_on_lines_when_unset(self):
        po = self._create_obligation(perf_type="income", total_amount=300.0)
        self.assertFalse(po.analytic_distribution)
        move = po._recognize(100, "2026-01-31", "Jan")
        self.assertFalse(any(move.line_ids.mapped("analytic_distribution")))

    def test_distribution_on_expense_obligation(self):
        po = self._create_obligation(perf_type="expense", total_amount=300.0)
        po.analytic_distribution = self._distribution()
        move = po._recognize(100, "2026-01-31", "Jan")
        pl_line = move.line_ids.filtered(lambda line: line.account_id == self.exp_pl)
        self.assertEqual(pl_line.analytic_distribution, self._distribution())

    def test_posting_creates_a_single_analytic_item(self):
        po = self._create_obligation(
            perf_type="income", total_amount=300.0, state="in_progress"
        )
        po.analytic_distribution = self._distribution()
        move = po._recognize(100, "2026-01-31", "Jan")
        move.action_post()
        analytic_lines = self.env["account.analytic.line"].search(
            [("move_line_id", "in", move.line_ids.ids)]
        )
        self.assertEqual(len(analytic_lines), 1)
        self.assertEqual(analytic_lines.move_line_id.account_id, self.inc_pl)
        self.assertAlmostEqual(analytic_lines.amount, 100.0)
