==================================
Performance Obligations - Contract
==================================

Automatic performance obligation creation from contract lines, with
integration between sale orders and contracts.

Purpose
=======

This module automates the creation of **Performance Obligations** (IFRS 15)
when a contract line is created, based on the recognition configuration
defined on each product.

For each contract line whose product has **Auto-create Performance Obligation**
enabled and whose recognition method is set to *Based on contract dates*, a
performance obligation of type *income* is created and linked to that line.
The obligation's total amount is computed from the line's quantity and unit
price over the full contract period, and its start and end dates are taken
directly from the contract line's ``date_start`` and ``date_end``.

Contract lines without a ``date_end`` are skipped: a meaningful total amount
cannot be computed without a known end date.

When a contract line is created from a sale order line that already has a
linked performance obligation, the existing obligation is reused and linked
to the new contract line — no duplicate is created. The obligation's dates
and amount are updated to reflect the contract line's ``date_start`` and
``date_end``.

When a contract line is **cancelled** (``is_canceled`` set to ``True``), all
performance obligations linked to it are frozen: their total amount is updated
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
account).

Configuration
=============

#. On each relevant product, open the **Revenue Recognition** tab
   and configure:

   - Tick **Auto-create Performance Obligation**.
   - Select **Based on contract dates** as the **Revenue Recognition
     Duration** method. This option is only available on products that
     have **Is a contract** enabled.

Usage
=====

Direct contract line creation
------------------------------

#. Create a contract line directly on a contract whose product is
   configured for automatic obligation creation.
#. A performance obligation is automatically created for that line.
   Its start and end dates are set to the contract line's
   ``date_start`` and ``date_end`` respectively. The total amount is
   computed as::

       quantity_to_invoice(date_start, date_end) × unit_price

#. Use the **Performance Obligations** smart button on the contract
   form to review all obligations linked to that contract.

From a sale order
-----------------

#. Confirm a sale order containing a contract product configured for
   automatic obligation creation. A performance obligation is created
   on the sale order line, with dates derived from the line's
   ``date_start`` and ``date_end``.
#. When the contract is created from the sale order (via
   **Create Contract**), the existing performance obligation is
   automatically linked to the new contract line. Its dates and amount
   are updated to match the contract line.
#. No duplicate obligation is ever created in this flow.

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
