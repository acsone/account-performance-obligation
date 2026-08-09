## Why this module?

Without this module, performance obligations must be created and linked to
invoices manually. For companies selling products or services recognized over
time, this means setting up a separate obligation for every sale order line —
a repetitive and error-prone process.

This module removes that friction by creating obligations automatically at
order confirmation, computing dates and amounts from the product configuration,
and keeping obligations in sync with cancellations and re-confirmations.

## Companion modules

- **account_perf_obligation** *(required)*: provides the core performance
  obligation object and recognition engine.
- **account_perf_obligation_start_end_dates** *(required)*: provides the
  daily pro-rata recognition method and schedule generation; the sale
  integration relies on start and end dates being supported.
- **account_perf_obligation_auto_schedule** *(optional)*: automatically
  processes flagged obligations in the background, including those frozen
  on order cancellation.
