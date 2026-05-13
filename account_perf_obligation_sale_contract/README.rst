=====================================
Account Perf Obligation Sale Contract
=====================================

Bridge module between `account_perf_obligation_sale` and `account_perf_obligation_contract`

When a contract line is created from a sale order line that already has a
linked performance obligation, the existing obligation is reused and linked
to the new contract line — no duplicate is created. The obligation's dates
and amount are updated to reflect the contract line's ``date_start`` and
``date_end``.

Usage
=====

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
