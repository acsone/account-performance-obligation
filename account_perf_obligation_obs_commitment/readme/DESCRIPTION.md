This module extends [Performance Obligations (IFRS 15)](../account_perf_obligation)
to automatically record and maintain off-balance sheet commitment entries
linked to performance obligations.

## Features

- **Initial commitment entry**: when a performance obligation is created, a
  journal entry is posted immediately for the full commitment amount, using
  the income or expense commitment account depending on the obligation type.
- **Manual adjustment action**: a menu action lets the accountant trigger
  off-balance sheet adjustments at any chosen date. Odoo checks, for each
  obligation, whether the commitment balance still matches the remaining
  obligation (total amount minus already-recognized amount up to that date).
  If a gap exists, an adjustment entry is posted at the chosen date.
