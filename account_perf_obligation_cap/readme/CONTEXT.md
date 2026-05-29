## Why this module?

In some business situations the amount that can be recognized at any given
point in time must be restricted, independently of the recognition method
in use. Typical cases include:

- revenue recognition limited by a contractual milestone;
- a cap agreed with the client pending final acceptance;
- a temporary limit while a dispute is ongoing.

This module adds that restriction as a first-class feature on the obligation
form, with enforcement both in the manual recognition wizard and in the
automatic schedule generation.

## Companion modules

- **account_perf_obligation** *(required)*: provides the core performance
  obligation object and recognition engine.
- **account_perf_obligation_start_end_dates** *(recommended)*: provides
  schedule generation; without it, the schedule cap enforcement has no effect.
- **account_perf_obligation_auto_schedule** *(optional)*: automatically
  processes flagged obligations in the background when the cap changes.
