=======================
Account Perf Obligation
=======================

Manage Performance Obligations for income and expense recognition
according to `IFRS 15 <https://en.wikipedia.org/wiki/IFRS_15>`_.

Purpose
=======

IFRS 15 requires income (and symmetrically, expenses) to be recognized
when performance obligations are satisfied, regardless of when invoicing occurs.

This module introduces a **Performance Obligation** object that tracks:

- The total amount to be recognized
- Links to journal items (invoices, recognition entries)

A wizard allows manual recognition: given a cumulative target amount to recognize
at a given date, the module computes the adjustment needed and generates the
appropriate accrual or deferral journal entry.

A **Generate Schedule Entries** action allows generating all future
recognition journal entries in draft (with ``auto_post = at_date``),
based on the configured recognition method. Calling this action again
deletes existing draft entries and regenerates them, preserving any
already-posted entries.

In addition, this module provides a **flag-based mechanism** to keep
draft recognition entries in sync with changes that affect the schedule.
Whenever a relevant change is detected, the affected obligation is
flagged via ``schedule_needs_regeneration``. The actual regeneration
happens later, either:

- manually, through a list-view action that processes all flagged
  obligations, or
- automatically, when the optional companion module
  ``account_perf_obligation_auto_schedule`` is installed (which uses
  ``queue_job`` to process flagged obligations asynchronously, with
  an identity key on the obligation id to deduplicate concurrent
  requests).

Posted recognition entries are always preserved; only drafts are deleted
and regenerated. To avoid recursive marking during regeneration itself,
a ``perf_obligation_in_regeneration`` context flag is set while a
schedule is being rebuilt.

All computed amounts are derived from accounting entries, ensuring
the obligation state can be fully recomputed from the ledger at any time.

Configuration
=============

#. Go to **Invoicing > Configuration > Settings**
#. Under **Performance Obligations**, configure for each type (income/expense):

   - Recognition journal
   - Deferral account (balance sheet)
   - Accrual account (balance sheet)
   - Counterpart account (P&L)

Usage
=====

#. Go to **Invoicing > Performance Obligations**
#. Create a new obligation (type: income or expense, total amount)
#. On invoice journal items, set the **Performance Obligation** field
   to link them to the obligation
#. From the obligation form, use the **Recognize Income/Expense** action
   to open the recognition wizard
#. Enter the cumulative amount to recognize at the given date, and a description
#. Confirm: the module creates a draft accrual or deferral journal entry
   (with ``auto_post = at_date``)
#. Alternatively, use the **Generate Schedule Entries** button to
   automatically create draft recognition entries for each period
   until the end of the obligation
#. Use the **Journal Items** smart button to review all entries
   linked to the obligation

Negative obligations
====================

The ``total_amount`` field may be negative to model revenue reversals
(credit notes) or negative expense corrections.

When ``total_amount`` is negative the debit and credit balance-sheet
accounts configured on the company are **swapped** automatically by the
recognition engine, so the same accounting logic produces mirror-image
entries without any additional configuration.

The ``amount_to_recognize`` passed to the wizard must carry the **same
sign** as ``total_amount`` (or be zero, which always represents full
deferral regardless of sign). Passing a value whose absolute amount
exceeds that of ``total_amount`` is still rejected.

Automatic schedule regeneration
===============================

Once an obligation is configured to support scheduling (via an extension
module providing a recognition method and date range), it is automatically
flagged for regeneration whenever:

- the obligation is **created** with a complete configuration
- its **total amount** or **recognition method** is modified
- a journal item linked to the obligation is **created**, **modified**
  or **deleted**

The flag is exposed as the ``schedule_needs_regeneration`` boolean field
on ``perf.obligation`` and is shown in the obligation form view.

A dedicated **list-view filter** lets users find all obligations
needing regeneration, and a **server action** runs
``_process_pending_regenerations()`` on the selected obligations,
which calls ``_regenerate_schedule()`` on each one and clears the flag.

Posted recognition entries are never deleted; regeneration only affects
drafts and skips periods already covered by posted entries.

For high-volume installations, install
``account_perf_obligation_auto_schedule`` to have flagged obligations
processed asynchronously via ``queue_job``.

Extensibility
=============

The list of fields whose modification flags an obligation as needing
recognition review is returned by ``_get_recognition_trigger_fields()``
on ``perf.obligation``. Override this method in extension modules to
add fields that should also invalidate the schedule.

Two methods drive the marking flow on ``perf.obligation``:

- ``_mark_needs_recognition(account_date=None)`` is the public entry
  point, called whenever something changes that may affect the
  recognized amounts on an obligation: configuration changes, linked
  journal items being created, modified or removed, etc. The optional
  ``account_date`` parameter indicates the earliest date from which
  recognition needs to be reviewed (reserved for future extensions
  that may track per-date review state).

- ``_mark_for_regeneration()`` is the schedule-specific marker called
  internally by ``_mark_needs_recognition`` when the obligation
  supports scheduling. It sets ``schedule_needs_regeneration`` to
  ``True`` and returns the recordset of obligations actually flagged.
  It is a no-op when the ``perf_obligation_in_regeneration`` context
  flag is set, which is automatically the case while
  ``_regenerate_schedule()`` is running, preventing recursive marking.

The marking entry point ``_mark_needs_recognition`` is called from:

- ``perf.obligation.create`` and ``perf.obligation.write``
  (when a trigger field changes)
- ``account.move.line.create``, ``write`` and ``unlink``
  (for any line linked to an obligation)

Extension modules typically override:

- ``_get_recognition_trigger_fields()`` to add new trigger fields
- ``_mark_needs_recognition()`` to add side effects on any change
  affecting recognition (e.g. set a "needs review from" date field)
- ``_mark_for_regeneration()`` to react specifically to schedule
  invalidation (this is what ``account_perf_obligation_auto_schedule``
  does to enqueue an asynchronous job)
