This module extends [Performance Obligations (IFRS 15)](../account_perf_obligation)
to automate the creation of performance obligations directly from sale orders.

## Features

- **Automatic obligation creation**: when a sale order is confirmed, an income
  obligation is created for each line whose product has *Auto-create
  Performance Obligation* enabled. The total amount is the line's untaxed
  subtotal; start and end dates are derived from the product's recognition
  method.
- **P&L account mapping**: the obligation's *P&L Recognition Account* is
  resolved from the product's income account, with fiscal position mappings
  applied automatically.
- **Cancellation handling**: when a sale order is cancelled, all linked
  obligations are frozen at the already-invoiced amount (or set to zero if
  nothing has been invoiced yet). The next schedule regeneration generates
  the adjustment entries automatically.
- **Re-confirmation handling**: when a cancelled order is re-confirmed,
  existing obligations are updated in place — dates, total amount, and P&L
  account are recomputed as if the obligation were being created for the
  first time. No duplicate is created.
- **Smart button**: a *Performance Obligations* smart button on the sale order
  form gives quick access to all obligations linked to that order.
