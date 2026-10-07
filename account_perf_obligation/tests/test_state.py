# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

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

    def test_default_state_is_open_and_not_in_service(self):
        po = self.env["perf.obligation"].create(
            {
                "perf_type": "income",
                "total_amount": 1000.0,
                "company_id": self.company.id,
            }
        )
        self.assertEqual(po.state, "open")
        self.assertTrue(po.not_in_service)

    def test_start(self):
        po = self._create_obligation()
        self.assertTrue(po.not_in_service)
        po._start()
        self.assertFalse(po.not_in_service)
        self.assertEqual(po.state, "open")
        # Starting an obligation already in service is a no-op.
        po._start()
        self.assertFalse(po.not_in_service)

    def test_recognition_move_cannot_be_posted_when_not_in_service(self):
        po = self._create_obligation()
        move = po._recognize(100, "2026-01-31", "Jan")
        with self.assertRaisesRegex(UserError, "is not in service"):
            move.action_post()

    def test_invoice_can_be_posted_when_not_in_service(self):
        po = self._create_obligation()
        invoice = self._post_invoice(po, 1000)
        self.assertEqual(invoice.state, "posted")
        # Only obligations in service are closed automatically.
        self.assertEqual(po.state, "open")
        self.assertTrue(po.not_in_service)

    def test_done_blocks_writes(self):
        po = self._create_obligation(not_in_service=False)
        po.write({"state": "done"})
        with self.assertRaises(UserError):
            po.total_amount = 1.0
        with self.assertRaises(UserError):
            po.unlink()

    def test_done_blocks_not_in_service_change(self):
        po = self._create_obligation(not_in_service=False)
        po.write({"state": "done"})
        with self.assertRaises(UserError):
            po.not_in_service = True

    def test_done_blocks_recognition_entry_posting(self):
        po = self._create_obligation(not_in_service=False)
        move = po._recognize(100, "2026-01-31", "Jan")
        po.write({"state": "done"})
        with self.assertRaisesRegex(UserError, "is done"):
            move.action_post()

    def test_posting_invoice_reopens_done_obligation(self):
        po = self._create_obligation(not_in_service=False)
        po.write({"state": "done"})
        self._post_invoice(po, 100)
        self.assertEqual(po.state, "open")

    def test_posting_credit_note_reopens_done_obligation(self):
        po = self._create_obligation()
        invoice = self._post_invoice(po, 1000)
        po._start()
        po.action_done()
        credit_note = invoice._reverse_moves([{"ref": "Price difference"}])
        credit_note.action_post()
        self.assertEqual(credit_note.state, "posted")
        self.assertEqual(po.state, "open")

    def test_action_done_requires_recognized_and_invoiced_amounts(self):
        po = self._create_obligation(not_in_service=False)
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

    def test_action_done_blocked_when_not_in_service(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        with self.assertRaisesRegex(UserError, "not in service"):
            po.action_done()
        self.assertEqual(po.state, "open")

    def test_action_done_and_reopen(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._start()
        po.action_done()
        self.assertEqual(po.state, "done")
        po.action_reopen()
        self.assertEqual(po.state, "open")
        self.assertFalse(po.not_in_service)

    def test_auto_done_when_last_movement_is_an_invoice(self):
        po = self._create_obligation(not_in_service=False)
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")

    def test_no_auto_done_when_not_fully_invoiced(self):
        po = self._create_obligation(not_in_service=False)
        self._post_invoice(po, 400)
        self.assertEqual(po.state, "open")

    def test_post_all_only_posts_obligations_in_service(self):
        po_in_service = self._create_obligation(total_amount=2000, not_in_service=False)
        po_not_in_service = self._create_obligation(total_amount=2000)
        for po in (po_in_service, po_not_in_service):
            self._post_invoice(po, 1000)
        move_in_service = po_in_service._recognize(500, "2026-01-31", "Jan")
        move_not_in_service = po_not_in_service._recognize(500, "2026-01-31", "Jan")
        self.env["perf.obligation"]._post_all_recognition_moves(
            fields.Date.from_string("2026-01-31")
        )
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move_in_service.state, "posted")
        self.assertEqual(move_not_in_service.state, "draft")

    def test_post_all_postpones_only_open_obligations_not_in_service(self):
        """The postpone hook is called on the open obligations flagged as
        not in service, and only on those."""
        po_not_in_service = self._create_obligation()
        po_in_service = self._create_obligation(not_in_service=False)
        po_done = self._create_obligation(not_in_service=False)
        po_done.write({"state": "done"})
        date = fields.Date.from_string("2026-01-31")
        with patch.object(
            type(po_not_in_service),
            "_postpone_not_in_service_obligations",
            autospec=True,
        ) as postpone:
            self.env["perf.obligation"]._post_all_recognition_moves(date)
        postpone.assert_called_once()
        obligations, postpone_date = postpone.call_args.args
        self.assertEqual(postpone_date, date)
        self.assertIn(po_not_in_service, obligations)
        self.assertNotIn(po_in_service, obligations)
        self.assertNotIn(po_done, obligations)

    def test_update_from_source_reopens_done_obligation(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._start()
        po.action_done()
        self.assertEqual(po.state, "done")
        po._update_total_amount(1500.0, "More quantities delivered")
        self.assertEqual(po.state, "open")
        self.assertEqual(po.total_amount, 1500.0)

    def test_update_from_source_unchanged_keeps_done(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._start()
        po.action_done()
        po._update_total_amount(po.total_amount, "No change")
        self.assertEqual(po.state, "done")

    def test_manual_write_still_blocked_when_done(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._start()
        po.action_done()
        with self.assertRaises(UserError):
            po.total_amount = 1500.0
