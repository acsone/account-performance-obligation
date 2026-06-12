## Why this module?

Under IFRS 15, entities may need to disclose the remaining performance
obligations not yet recognized as revenue or expense. Standard Odoo has no
built-in mechanism to track these commitments off-balance sheet.

This module automates that tracking: a commitment entry is posted when an
obligation is created, and a manual action keeps it in sync with the
recognized amounts at any chosen date — giving the accountant full control
over when adjustments are posted.

## Companion modules

- **account_perf_obligation** *(required)*: provides the core performance
  obligation object.
