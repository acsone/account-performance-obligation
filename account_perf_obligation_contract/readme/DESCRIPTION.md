This module extends [Performance Obligations (IFRS 15)](../account_perf_obligation)
to automate the creation of performance obligations directly from contract lines.

## Features

- **Automatic obligation creation**: when a contract line is saved with
  *Auto-create Performance Obligation* ticked, an obligation is created and
  linked to that line. Its total amount is computed from the contract line
  value over the full contract period; start and end dates are taken from
  the contract line's `date_start` and `date_end`.
- **P&L account mapping**: the obligation's *P&L Recognition Account* is set
  to the account that would appear on the generated invoice line, respecting
  fiscal position mappings.
- **Cancellation handling**: when a contract line is cancelled, its linked
  obligation is frozen at the already-invoiced amount (or set to zero if
  nothing has been invoiced yet). The next schedule regeneration generates
  the adjustment entries automatically.
- **Deletion handling**: when a contract line is deleted, its linked
  obligation is deleted too. Deletion is blocked if posted accounting entries
  are linked to the obligation; draft entries are deleted automatically.
- **Invoice propagation**: when Odoo generates a recurring invoice from a
  contract line that carries an obligation, the obligation is automatically
  copied to the corresponding invoice line and accounting entry.
- **Smart button**: a *Performance Obligations* smart button on the contract
  form gives quick access to all obligations linked to that contract.

> Contract lines without a `date_end` are not eligible for automatic
> obligation creation.
