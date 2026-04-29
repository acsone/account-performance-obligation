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
