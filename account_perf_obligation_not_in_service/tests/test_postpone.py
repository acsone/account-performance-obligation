# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPostponeNotInService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.income_account = cls.env["account.account"].create(
            {
                "name": "Income Test",
                "code": "707NIS",
                "account_type": "income",
            }
        )
        cls.inc_pl = cls.env["account.account"].create(
            {
                "name": "Income Reco P&L",
                "code": "7R1NIS",
                "account_type": "income",
            }
        )
        cls.inc_debit_bs = cls.env["account.account"].create(
            {
                "name": "Income Accrual BS",
                "code": "418NIS",
                "account_type": "asset_current",
            }
        )
        cls.inc_credit_bs = cls.env["account.account"].create(
            {
                "name": "Income Deferral BS",
                "code": "487NIS",
                "account_type": "liability_current",
            }
        )
        cls.reco_journal = cls.env["account.journal"].create(
            {
                "name": "Income Reco Journal",
                "code": "RNIS",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.company.write(
            {
                "po_income_journal_id": cls.reco_journal.id,
                "po_income_pl_account_id": cls.inc_pl.id,
                "po_income_debit_bs_account_id": cls.inc_debit_bs.id,
                "po_income_credit_bs_account_id": cls.inc_credit_bs.id,
            }
        )

    def _make_po(self, **overrides):
        vals = {
            "perf_type": "income",
            "total_amount": 900.0,
            "company_id": self.company.id,
            "recognition_at_date_method": "daily",
            "start_date": date(2026, 11, 1),
            "end_date": date(2027, 2, 27),
            "not_in_service": True,
        }
        vals.update(overrides)
        return self.env["perf.obligation"].create(vals)

    def test_default_is_in_service(self):
        po = self.env["perf.obligation"].create(
            {
                "perf_type": "income",
                "total_amount": 500.0,
                "company_id": self.company.id,
            }
        )
        self.assertFalse(po.not_in_service)

    def test_postpone_moves_start_date_to_first_day_of_next_month(self):
        po = self._make_po()
        po._postpone_not_in_service_obligations(date(2026, 11, 30))
        self.assertEqual(po.start_date, date(2026, 12, 1))
        self.assertEqual(po.end_date, date(2027, 2, 27))
        self.assertTrue(po.not_in_service)
        self.assertEqual(po.state, "open")

    def test_postpone_ignores_obligation_starting_after_the_date(self):
        po = self._make_po(start_date=date(2026, 12, 15))
        po._postpone_not_in_service_obligations(date(2026, 11, 30))
        self.assertEqual(po.start_date, date(2026, 12, 15))

    def test_postpone_ignores_obligation_in_service(self):
        po = self._make_po(not_in_service=False)
        po._postpone_not_in_service_obligations(date(2026, 11, 30))
        self.assertEqual(po.start_date, date(2026, 11, 1))

    def test_postpone_ignores_done_obligation(self):
        po = self._make_po(state="done")
        po._postpone_not_in_service_obligations(date(2026, 11, 30))
        self.assertEqual(po.start_date, date(2026, 11, 1))

    def test_postpone_after_end_date_raises(self):
        po = self._make_po(end_date=date(2026, 11, 30))
        with self.assertRaisesRegex(UserError, "after its end date"):
            po._postpone_not_in_service_obligations(date(2026, 11, 30))

    def test_postpone_one_day_obligation_moves_both_dates(self):
        po = self._make_po(start_date=date(2026, 11, 1), end_date=date(2026, 11, 1))
        po._postpone_not_in_service_obligations(date(2026, 11, 30))
        self.assertEqual(po.start_date, date(2026, 12, 1))
        self.assertEqual(po.end_date, date(2026, 12, 1))
        self.assertTrue(po.not_in_service)

    def test_post_all_postpones_obligation_not_in_service_and_posts_nothing(self):
        po = self._make_po()
        po._regenerate_schedule()
        self.env["perf.obligation"]._post_all_recognition_moves(date(2026, 11, 30))
        self.assertEqual(po.start_date, date(2026, 12, 1))
        self.assertFalse(po.schedule_needs_regeneration)
        drafts = po._get_draft_schedule_moves()
        self.assertTrue(drafts)
        self.assertTrue(all(move.auto_post == "no" for move in drafts))
        self.assertNotIn(date(2026, 11, 30), drafts.mapped("date"))

    def test_post_all_mixed_postpones_not_in_service_and_marks_in_service(self):
        po_nis = self._make_po()
        po_nis._regenerate_schedule()
        po_active = self._make_po(not_in_service=False)
        po_active._regenerate_schedule()
        nov_active_move = po_active._get_draft_schedule_moves().filtered(
            lambda m: m.date == date(2026, 11, 30)
        )
        self.assertTrue(nov_active_move)

        self.env["perf.obligation"]._post_all_recognition_moves(date(2026, 11, 30))

        self.assertEqual(po_nis.start_date, date(2026, 12, 1))
        self.assertTrue(
            all(m.auto_post == "no" for m in po_nis._get_draft_schedule_moves())
        )
        self.assertEqual(nov_active_move.auto_post, "at_date")

    def test_action_post_blocked_when_not_in_service(self):
        po = self._make_po()
        move = po._recognize(100.0, date(2026, 11, 30), "Nov")
        with self.assertRaisesRegex(UserError, "Not in Service"):
            move.action_post()
        self.assertEqual(move.state, "draft")

        po._start()
        move.action_post()
        self.assertEqual(move.state, "posted")
