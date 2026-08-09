## Why this module?

Without this module, performance obligations must be created and linked to
invoices manually. For companies using the *Contracts* module (recurring
billing), this is tedious and error-prone: every new contract line would
require a separate obligation to be set up by hand.

This module removes that friction by creating obligations automatically
from contract lines, keeping amounts and dates in sync with the contract,
and propagating the obligation to each generated invoice line.

## Companion modules

- **account_perf_obligation** *(required)*: provides the core performance
  obligation object and recognition engine.
- **account_perf_obligation_start_end_dates** *(required)*: provides the
  daily pro-rata recognition method and schedule generation; the contract
  integration relies on start and end dates being supported.
- **account_perf_obligation_auto_schedule** *(optional)*: automatically
  processes flagged obligations in the background, including those frozen
  on contract line cancellation.
