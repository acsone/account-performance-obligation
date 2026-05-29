## Why this module?

The base *Performance Obligations* module flags obligations for schedule
regeneration whenever a relevant change is detected (total amount, dates,
recognition method, linked journal items). By default, processing is manual:
a user must explicitly trigger the regeneration via a list-view action.

In high-volume installations, synchronous regeneration would slow down
user operations such as invoice posting or mass updates. This module
removes that friction by offloading regeneration entirely to the
`queue_job` background worker.

## Companion modules

- **account_perf_obligation** *(required)*: provides the core performance
  obligation object and the flagging mechanism.
- **account_perf_obligation_start_end_dates** *(recommended)*: provides the
  daily pro-rata recognition method and schedule date range; without it,
  no schedule will be generated.
