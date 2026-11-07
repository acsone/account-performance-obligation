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

    def test_default_state_is_open(self):
        po = self._create_obligation()
        self.assertEqual(po.state, "open")

    def test_done_blocks_writes(self):
        po = self._create_obligation()
        po.write({"state": "done"})
        with self.assertRaises(UserError):
            po.total_amount = 1.0
        with self.assertRaises(UserError):
            po.unlink()

    def test_done_blocks_schedule_generation(self):
        po = self._create_obligation()
        po.write({"state": "done"})
        with self.assertRaisesRegex(UserError, "no longer be regenerated"):
            po.action_generate_schedule()

    def test_done_blocks_recognition_entry_posting(self):
        po = self._create_obligation()
        move = po._recognize(100, "2026-01-31", "Jan")
        po.write({"state": "done"})
        with self.assertRaisesRegex(UserError, "is done"):
            move.action_post()

    def test_posting_invoice_reopens_done_obligation(self):
        po = self._create_obligation()
        po.write({"state": "done"})
        self._post_invoice(po, 100)
        self.assertEqual(po.state, "open")

    def test_posting_credit_note_reopens_done_obligation(self):
        po = self._create_obligation()
        invoice = self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")
        credit_note = invoice._reverse_moves([{"ref": "Price difference"}])
        credit_note.action_post()
        self.assertEqual(credit_note.state, "posted")
        self.assertEqual(po.state, "open")

    def test_action_done(self):
        po = self._create_obligation(total_amount=1500.0)
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "open")
        # Nothing is posted anymore: the obligation is closed manually.
        po.total_amount = 1000.0
        po.action_done()
        self.assertEqual(po.state, "done")

    def test_action_done_only_from_open(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")
        with self.assertRaisesRegex(UserError, "Only an open obligation"):
            po.action_done()

    def test_action_done_requires_recognized_and_invoiced_amounts(self):
        po = self._create_obligation()
        self._post_invoice(po, 400)
        with self.assertRaisesRegex(UserError, "cannot be set to done"):
            po.action_done()

    def test_action_done_blocked_by_draft_moves(self):
        po = self._create_obligation()
        po._recognize(500, "2026-01-31", "Jan")
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "open")
        with self.assertRaisesRegex(UserError, "draft journal entries"):
            po.action_done()

    def test_action_reopen(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")
        po.action_reopen()
        self.assertEqual(po.state, "open")
        po.total_amount = 1500.0
        self.assertEqual(po.total_amount, 1500.0)

    def test_auto_done_when_last_movement_is_an_invoice(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")

    def test_no_auto_done_when_not_fully_invoiced(self):
        po = self._create_obligation()
        self._post_invoice(po, 400)
        self.assertEqual(po.state, "open")

    def test_post_all_does_not_post_done_obligations(self):
        po_open = self._create_obligation(total_amount=2000)
        po_done = self._create_obligation(total_amount=2000)
        for po in (po_open, po_done):
            self._post_invoice(po, 1000)
        move_open = po_open._recognize(500, "2026-01-31", "Jan")
        move_done = po_done._recognize(500, "2026-01-31", "Jan")
        po_done.write({"state": "done"})
        self.env["perf.obligation"]._post_all_recognition_moves(
            fields.Date.from_string("2026-01-31")
        )
        self.env["account.move"]._autopost_draft_entries()
        self.assertEqual(move_open.state, "posted")
        self.assertEqual(move_done.state, "draft")

    def test_update_from_source_reopens_done_obligation(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")
        po._update_total_amount(1500.0, "More quantities delivered")
        self.assertEqual(po.state, "open")
        self.assertEqual(po.total_amount, 1500.0)

    def test_update_from_source_unchanged_keeps_done(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        po._update_total_amount(po.total_amount, "No change")
        self.assertEqual(po.state, "done")

    def test_manual_write_still_blocked_when_done(self):
        po = self._create_obligation()
        self._post_invoice(po, 1000)
        self.assertEqual(po.state, "done")
        with self.assertRaises(UserError):
            po.total_amount = 1500.0
