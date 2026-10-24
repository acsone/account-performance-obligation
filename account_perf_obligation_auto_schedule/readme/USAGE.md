## Normal operation

Once installed and `queue_job` is running, no manual steps are required.
When an obligation is flagged for regeneration — following a configuration
change, or any other triggering event — a job is automatically enqueued
to rebuild its draft schedule in the background.

## Monitor jobs

Go to *Job Queue > Queue > Jobs* to monitor pending and completed
regeneration jobs.

## Force immediate processing

The **Process Pending Regenerations** list-view action from the base module
remains available. Use it to force synchronous regeneration on selected
obligations without waiting for the queue worker.
