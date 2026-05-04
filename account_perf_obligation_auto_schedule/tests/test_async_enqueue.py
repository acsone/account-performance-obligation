# Copyright 2026 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from unittest.mock import patch

from odoo import Command

from odoo.addons.account_perf_obligation.tests.common import (
    PerfObligationCommon,
)
from odoo.addons.queue_job.tests.common import trap_jobs


class TestAsyncEnqueue(PerfObligationCommon):
    """Unit tests for async job enqueueing.

    These tests verify that `_mark_for_regeneration` correctly enqueues
    a `queue_job` when an obligation supports scheduling. Since the base
    module's `_supports_schedule()` always returns False, we patch it
    to return True for the duration of each test.

    These tests do NOT depend on any recognition-method implementation;
    they only verify the enqueueing layer.
    """

    # =========================================================
    # A job is enqueued on marking
    # =========================================================

    def test_create_enqueues_job(self):
        """Creating a flagged obligation enqueues a regeneration job."""
        with (
            patch.object(
                type(self.env["perf.obligation"]),
                "_supports_schedule",
                return_value=True,
            ),
            trap_jobs() as trap,
        ):
            po = self._create_obligation()
            self.assertTrue(po.schedule_needs_regeneration)
            trap.assert_jobs_count(1, only=po._process_pending_regenerations)

    def test_change_total_amount_enqueues_job(self):
        """Changing total_amount enqueues a job."""
        po = self._create_obligation(total_amount=1000)
        with (
            patch.object(type(po), "_supports_schedule", return_value=True),
            trap_jobs() as trap,
        ):
            po.total_amount = 2000
            trap.assert_jobs_count(1, only=po._process_pending_regenerations)

    def test_change_recognition_method_enqueues_job(self):
        po = self._create_obligation()
        with (
            patch.object(type(po), "_supports_schedule", return_value=True),
            trap_jobs() as trap,
        ):
            po.write({"recognition_at_date_method": False})
            trap.assert_jobs_count(1, only=po._process_pending_regenerations)

    def test_post_invoice_enqueues_job(self):
        po = self._create_obligation(perf_type="income", total_amount=1000)
        with (
            patch.object(type(po), "_supports_schedule", return_value=True),
            trap_jobs() as trap,
        ):
            self._create_and_post_move(
                self.sale_journal,
                [
                    (self.receivable_account, 1000, 0, False),
                    (self.income_account, 0, 1000, po),
                ],
            )
            trap.assert_jobs_count(1, only=po._process_pending_regenerations)

    # =========================================================
    # Identity key: no duplicate jobs per obligation
    # =========================================================

    def test_multiple_changes_deduplicate_via_identity_key(self):
        """Multiple triggering events on the same obligation enqueue
        only one pending job thanks to the identity key."""
        po = self._create_obligation(total_amount=1000)
        with (
            patch.object(type(po), "_supports_schedule", return_value=True),
            trap_jobs() as trap,
        ):
            po.total_amount = 2000
            po.total_amount = 3000
            po.description = "ignored"  # not a trigger field
            po.recognition_at_date_method = False
            # Identity key deduplicates: still only 1 job
            trap.assert_jobs_count(1, only=po._process_pending_regenerations)

    def test_changes_on_different_obligations_enqueue_distinct_jobs(self):
        """Changes on two different obligations enqueue two distinct
        jobs (identity key is per-record)."""
        po1 = self._create_obligation(total_amount=1000)
        po2 = self._create_obligation(total_amount=1000)
        with (
            patch.object(type(po1), "_supports_schedule", return_value=True),
            trap_jobs() as trap,
        ):
            po1.total_amount = 2000
            po2.total_amount = 2000
            self.assertEqual(len(trap.enqueued_jobs), 2)

    # =========================================================
    # No job for unsupported obligations
    # =========================================================

    def test_no_job_when_unsupported(self):
        """An obligation without schedule support does not enqueue."""
        with trap_jobs() as trap:
            po = self._create_obligation(total_amount=1000)
            self.assertFalse(po.schedule_needs_regeneration)
            trap.assert_jobs_count(0)

    # =========================================================
    # Recursion guard
    # =========================================================

    def test_no_job_when_in_regeneration_context(self):
        """The perf_obligation_in_regeneration context flag prevents
        job enqueueing."""
        po = self._create_obligation(perf_type="income", total_amount=1000)
        with (
            patch.object(type(po), "_supports_schedule", return_value=True),
            trap_jobs() as trap,
        ):
            self.env["account.move"].with_context(
                perf_obligation_in_regeneration=True
            ).create(
                {
                    "journal_id": self.sale_journal.id,
                    "date": "2026-01-01",
                    "line_ids": [
                        Command.create(
                            {
                                "account_id": self.receivable_account.id,
                                "debit": 1000,
                                "credit": 0,
                                "name": "Test",
                            },
                        ),
                        Command.create(
                            {
                                "account_id": self.income_account.id,
                                "debit": 0,
                                "credit": 1000,
                                "name": "Test",
                                "perf_obligation_id": po.id,
                            },
                        ),
                    ],
                }
            )
            trap.assert_jobs_count(0)
