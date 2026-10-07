# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields
from odoo.exceptions import UserError

from .common import PerfObligationCommon


class TestState(PerfObligationCommon):
    def _post_invoice(self, po, amount):
        return self._create_and_post_move(
            self.sale_journal,
            [
                (self.receivable_account, amount, 0, False),
                (self.income_account, 0, amount, po),
            ],
        )

    def test_default_state_is_draft(self):
        po = self.env["perf.obligation"].create(
            {
                "perf_type": "income",
                "total_amount": 1000.0,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(po.state, "draft")

    def test_start(self):
        po = self._create_obligation()
        po.action_start()
        self.assertEqual(po.state, "in_progress")
        with self.assertRaises(UserError):
            po.action_start()

    def test_recognition_move_cannot_be_posted_on_draft(self):
        po = self._create_obligation()
        move = po._recognize(100, "2026-01-31", "Jan")
        with self.assertRaisesRegex(UserError, "is not in progress"):
            move.action_post()

    def test_invoice_can_be_posted_on_draft(self):
        po = self._create_obligation()
        invoice = self._post_invoice(po, 1000)
        self.assertEqual(invoice.state, "posted")
        # Only 'in progress' obligations are closed automatically.
        self.assertEqual(po.state, "draft")

    def test_done_blocks_posting_and_writes(self):
        po = self._create_obligation(state="in_progress")
        po.write({"state": "done"})
        with self.assertRaisesRegex(UserError, "is done"):
            self._post_invoice(po, 100)
        with self.assertRaises(UserError):
            po.total_amount = 1.0
        with self.assertRaises(UserError):
            po.unlink()

    def test_action_done_requires_recognized_and_invoiced_amounts(self):
        po = self._create_obligation(state="in_progress")
        self._post_invoice(po, 400)
        with self.assertRaisesRegex(UserError, "cannot be set to done"):
            po.action_done()

    def test_action_done_blocked_by_draft_moves(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._recognize(500, "2026-01-31", "Jan")
        po._start()
        with self.assertRaisesRegex(UserError, "draft journal entries"):
            po.action_done()

    def test_action_done_and_reopen(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._start()
        po.action_done()
        self.assertEqual(po.state, "done")
        po.action_reopen()
        self.assertEqual(po.state, "in_progress")

    def test_auto_done_when_last_movement_is_an_invoice(self):
        po = self._create_obligation(state="in_progress")
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")

    def test_no_auto_done_when_not_fully_invoiced(self):
        po = self._create_obligation(state="in_progress")
        self._post_invoice(po, 400)
        self.assertEqual(po.state, "in_progress")

    def test_post_all_only_posts_in_progress_obligations(self):
        po_progress = self._create_obligation(total_amount=2000, state="in_progress")
        po_draft = self._create_obligation(total_amount=2000)
        for po in (po_progress, po_draft):
            self._post_invoice(po, 1000)
        move_progress = po_progress._recognize(500, "2026-01-31", "Jan")
        move_draft = po_draft._recognize(500, "2026-01-31", "Jan")
        self.env["perf.obligation"]._post_all_recognition_moves(
            fields.Date.from_string("2026-01-31")
        )
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move_progress.state, "posted")
        self.assertEqual(move_draft.state, "draft")
