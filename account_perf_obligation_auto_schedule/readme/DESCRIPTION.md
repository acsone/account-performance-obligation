This module extends [Performance Obligations (IFRS 15)](../account_perf_obligation)
to process flagged obligations **automatically and asynchronously** via
[queue_job](https://github.com/OCA/queue/tree/18.0/queue_job).

## Features

- Whenever an obligation is flagged for schedule regeneration, a `queue_job`
  is automatically enqueued to rebuild its draft schedule in the background.
- **Deduplication via identity key**: if a job is already queued for an
  obligation and a new triggering event occurs, no duplicate job is created —
  the existing job picks up the latest state when it runs.
- The manual **Process Pending Regenerations** action from the base module
  remains available as a fallback for administrators who want to force
  immediate processing.
