## Developer extensibility

The module is designed to be extended by companion modules.

**Trigger fields**

The list of fields whose modification flags an obligation as needing recognition
review is returned by `_get_recognition_trigger_fields()` on `perf.obligation`.
Override this method to add fields that should also invalidate the schedule.

**Marking flow**

Two methods drive the marking flow:

- `_mark_needs_recognition(account_date=None)` — entry point called
  whenever something changes that may affect recognized amounts (configuration
  changes, linked journal items created/modified/removed). The optional
  `account_date` parameter indicates the earliest date from which recognition
  needs review.
- `_mark_for_regeneration()` — schedule-specific marker called internally by
  `_mark_needs_recognition`. Sets `schedule_needs_regeneration = True` and
  returns the flagged obligations. It is a no-op when the context flag
  `perf_obligation_in_regeneration` is set (automatically active while
  `_regenerate_schedule()` runs, preventing recursive marking).

**Typical extension points**

- Override `_get_recognition_trigger_fields()` to add new trigger fields.
- Override `_mark_needs_recognition()` to add side effects on any change
  affecting recognition (e.g. set a "needs review from" date field).
- Override `_mark_for_regeneration()` to react specifically to schedule
  invalidation — this is what `account_perf_obligation_auto_schedule` does to
  enqueue an asynchronous `queue_job`.
