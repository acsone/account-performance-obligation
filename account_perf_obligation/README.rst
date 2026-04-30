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

The list of fields whose modification flags an obligation for
regeneration is returned by
``_get_schedule_regenerate_trigger_fields()`` on ``perf.obligation``.
Override this method in extension modules to add fields that should
also invalidate the draft schedule.

The marking entry point is ``_mark_for_regeneration()``, called from:

- ``perf.obligation.create`` and ``perf.obligation.write``
  (when a trigger field changes)
- ``account.move.line.create``, ``write`` and ``unlink``
  (for any line linked to an obligation)

This method is a no-op when:

- the obligation does not support scheduling
  (``_supports_schedule()`` returns ``False``), or
- the ``perf_obligation_in_regeneration`` context flag is set,
  which is automatically the case while ``_regenerate_schedule()``
  is running, preventing recursive marking.
