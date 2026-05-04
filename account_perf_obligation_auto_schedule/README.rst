=====================================================
Performance Obligations - Async Schedule Regeneration
=====================================================

Process flagged performance obligations asynchronously via ``queue_job``.

Purpose
=======

The base module ``account_perf_obligation`` flags obligations for
schedule regeneration via the ``schedule_needs_regeneration`` boolean
field. By default, processing is **manual**: a list-view action lets
users regenerate the schedules for selected obligations.

This module makes processing **automatic and asynchronous**. Whenever
an obligation is flagged, a ``queue_job`` is enqueued to process the
regeneration in the background.

An **identity key** on the obligation id ensures that only one job
per obligation is ever pending at a time: if a job is already queued
for an obligation and a new triggering event occurs, no duplicate
job is created — the existing job will pick up the latest state when
it runs.

This is particularly useful in high-volume installations, where
synchronous regeneration would slow down user operations
(invoice posting, mass updates, etc.).

Configuration
=============

This module requires ``queue_job`` to be properly configured.
See `the queue_job documentation
<https://github.com/OCA/queue/tree/18.0/queue_job>`_ for details on
setting up the ``runner`` worker process.

Once installed, no further configuration is needed: jobs are
automatically enqueued whenever an obligation is flagged for
regeneration.

Usage
=====

#. Install the module
#. Ensure the ``queue_job`` runner is running
#. Operate normally: when an obligation is flagged for regeneration
   (via configuration changes, invoice posting, etc.), a job is
   automatically enqueued to rebuild its draft schedule
#. Monitor pending and completed jobs via **Settings > Technical >
   Queue / Jobs**

The list-view manual action **Process Pending Regenerations**
(from the base module) remains available as a fallback for
administrators who want to force immediate processing.
