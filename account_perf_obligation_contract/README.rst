==================================
Performance Obligations - Contract
==================================

Automatic performance obligation creation from contract lines.

Purpose
=======

This module automates the creation of **Performance Obligations** (IFRS 15)
when a contract line is created, based on a boolean.

For each contract line ticked for **Auto-create Performance Obligation**, a
performance obligation is created and linked to that line.
The obligation's total amount is computed from the contract line value over the
full contract period, and its start and end dates are taken
directly from the contract line's ``date_start`` and ``date_end``.

Contract lines without a ``date_end`` are skipped: a meaningful total amount
cannot be computed without a known end date.

The obligation's **P&L Recognition Account** is set to match the account
that would appear on the generated invoice line.

When a contract line is **cancelled** (``is_canceled`` set to ``True``), the
performance obligation linked to it is frozen: its total amount is updated
to match the already-invoiced amount on the line. If nothing has been invoiced
yet, the total amount is set to zero. Any excess already-recognized amount will
be reversed on the next schedule regeneration.

When a contract line is **deleted**, the linked performance obligation is also
deleted. Deletion is blocked if any posted accounting entry is linked to the
obligation; draft entries linked to the obligation are deleted automatically
before the obligation itself is removed.

When a contract invoice line is generated from a contract line that has a
linked performance obligation, the obligation is automatically carried over
to the invoice line (and the corresponding accounting entry on the revenue
or expense account).

Configuration
=============

#. On each relevant contract line:

   - Tick **Auto-create Performance Obligation**.

#. Optionally, set an **Income Account** (sale contracts) or **Expense
   Account** (purchase contracts) on the product. If set, this account is
   copied to the obligation's **P&L Recognition Account**, overriding the
   default account from the accounting configuration. If the contract has a
   fiscal position with an account mapping for that account, the mapped
   account is used instead.

Usage
=====

Direct contract line creation
------------------------------

#. Create a contract line directly on a contract and
   configure it for automatic obligation creation.
#. A performance obligation is automatically created for that line.
   Its start and end dates are set to the contract line's
   ``date_start`` and ``date_end`` respectively.
#. The obligation's **P&L Recognition Account** is set to the same account
   that Odoo would use on the invoice line generated from this contract line.
#. Use the **Performance Obligations** smart button on the contract
   form to review all obligations linked to that contract.

Cancellation and deletion
--------------------------

#. If a contract line is cancelled, its obligation is frozen at the
   already-invoiced amount automatically. Run **Process Pending
   Regenerations** (or install ``account_perf_obligation_auto_schedule``)
   to generate the corresponding adjustment entries.
#. If a contract line is deleted:

   - Deletion is **blocked** if posted accounting entries are linked
     to the obligation. Reverse those entries first.
   - Draft accounting entries linked to the obligation are deleted
     automatically.
   - The obligation itself is then deleted along with the contract line.

Invoicing
---------

#. When Odoo generates a recurring invoice from the contract, the
   performance obligation is automatically copied to each invoice line
   produced from a contract line that carries an obligation.

Known Limitations
=================

- Contract lines without a ``date_end`` are not eligible for automatic
  obligation creation.
- The scenarios of contract line termination (``stop``), suspension
  (``pause``), and renewal are not yet handled and will be addressed in
  future versions of this module.
