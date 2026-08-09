This module manages **Performance Obligations** for income and expense recognition
according to [IFRS 15](https://en.wikipedia.org/wiki/IFRS_15).

## Features

- Track performance obligations with their total amount to recognize and all
  related journal items (invoices, recognition entries).
- **Manual recognition wizard**: enter a cumulative target amount at a given date;
  the module computes the required adjustment and generates the appropriate
  accrual or deferral journal entry.
- **Generate Schedule Entries** *(requires `account_perf_obligation_start_end_dates`)*:
  automatically create all future recognition entries in draft
  (with `auto_post = at_date`) based on the configured recognition method.
  Re-running the action deletes existing drafts and regenerates them,
  preserving any already-posted entries.
- **Automatic schedule synchronization** *(requires `account_perf_obligation_start_end_dates`)*:
  obligations are flagged for regeneration whenever a relevant change is detected
  (total amount, recognition method, linked journal items). Flagged obligations
  can be processed manually via a list-view action, or automatically when the
  companion module `account_perf_obligation_auto_schedule` is installed.
- Support for **negative obligations** to model revenue reversals (credit notes)
  or negative expense corrections, with automatic swap of balance-sheet accounts.
- All computed amounts are derived from accounting entries, so the obligation
  state can be fully recomputed from the ledger at any time.
