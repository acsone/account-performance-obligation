==============================
Performance Obligations - Sale
==============================

Automatic performance obligation creation from sale orders.

Purpose
=======

This module automates the creation of **Performance Obligations** (IFRS 15)
when a sale order is confirmed, based on the recognition configuration
defined on each product (see ``account_perf_obligation_product``).

For each confirmed sale order line whose product has
**Auto-create Performance Obligation** enabled, a performance obligation
of type *income* is created and linked to that line. The obligation's
total amount is set to the line's untaxed subtotal, and its recognition
period is derived from the product's configured recognition method.

When a sale order is **cancelled**, all performance obligations linked to
its lines are immediately capped at zero by enabling the recognition cap
(see ``account_perf_obligation_cap``). If any amount had already been
recognized, the next schedule regeneration will produce a de-recognition
entry to bring the cumulative recognized amount back to zero.

Configuration
=============

#. Install ``account_perf_obligation_product`` and configure each relevant
   product's **Revenue/Expense Recognition** tab (recognition method and,
   if applicable, duration in months).

Usage
=====

#. Confirm a sale order that contains lines with products configured for
   automatic obligation creation.
#. A performance obligation is automatically created for each qualifying
   line. Its start and end dates are computed as follows:

   - **At once**: start and end date are both set to the order
     confirmation date. The full amount is recognized on that day.
   - **Over several months**: start date is the order confirmation date;
     end date is the confirmation date plus the number of months
     configured on the product.

#. Use the **Performance Obligations** smart button on the sale order
   form to review all obligations linked to that order.
#. If the order is cancelled, the obligations are capped at zero
   automatically. Run **Process Pending Regenerations** (or install
   ``account_perf_obligation_auto_schedule``) to generate the
   corresponding de-recognition entries.
