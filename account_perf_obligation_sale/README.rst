==============================
Performance Obligations - Sale
==============================

Automatic performance obligation creation from sale orders.

Purpose
=======

This module automates the creation of **Performance Obligations** (IFRS 15)
when a sale order is confirmed, based on the recognition configuration
defined on each product.

For each confirmed sale order line whose product has
**Auto-create Performance Obligation** enabled, a performance obligation
of type *income* is created and linked to that line. The obligation's
total amount is set to the line's untaxed subtotal, and its recognition
period is derived from the product's configured recognition method.

When a sale order is **cancelled**, all performance obligations linked to
its lines are frozen: their total amount is updated to match the
already-invoiced amount on the line. If nothing has been invoiced yet,
the total amount is set to zero. Any excess already-recognized amount
will be reversed on the next schedule regeneration.

Configuration
=============

#. On each relevant product, open the **Revenue Recognition** tab
   and configure:

   - Tick **Auto-create Performance Obligation**.
   - Select a **Revenue Recognition Duration** method:

     - **At once**: the full amount is recognized on the order
       confirmation date.
     - **Over several months**: enter the number of months in the
       **Recognition Duration (months)** field that appears below.

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
#. If the order is cancelled, the obligations are frozen at their
   invoiced amount automatically. Run **Process Pending Regenerations**
   (or install ``account_perf_obligation_auto_schedule``) to generate
   the corresponding adjustment entries.
