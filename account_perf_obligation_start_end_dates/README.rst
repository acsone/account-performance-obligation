==================================================
Performance Obligations - Start/End Dates
==================================================

Extends the **Performance Obligations (IFRS 15)** module to support
time-based income and expense recognition using start and end dates.

Purpose
=======

When a performance obligation spans a defined period, this module computes
the amount to recognize at any given date using the **daily pro-rata** method.

It also provides the date range needed for **schedule generation**:
the **Generate Schedule Entries** button (from the base module) generates
draft recognition entries for each month-end from start date until the end
date, skipping periods already covered by posted entries.

This module also extends the **flag-based schedule regeneration**
mechanism from the base module: changes to the obligation's
**start date** or **end date** flag the obligation via
``schedule_needs_regeneration`` (in addition to the triggers already
handled by the base module: total amount, recognition method, linked
journal items). The flagged obligations are then regenerated either
manually through the list-view action or asynchronously, when the
optional ``account_perf_obligation_auto_schedule`` companion module
is installed.

The architecture is designed so that alternative computation methods
(e.g. full-month based) can be easily added by extending the selection
field and implementing the corresponding method.

Usage
=====

#. On a performance obligation, select a **Recognition at Date Method**
   (e.g. "Daily Pro-Rata")
#. Fill in the **Start Date** and **End Date**
   (these fields appear and become required when the daily pro-rata
   method is selected)
#. When opening the **Recognize Income/Expense** wizard, the
   **Amount to Recognize** field is automatically pre-filled based on
   the selected date and the obligation period, but can be modified
   before confirmation
#. As soon as the obligation has a method, a start date and an end date,
   it is automatically flagged for schedule regeneration; subsequent
   changes to the dates, total amount, recognition method or linked
   journal items will re-flag the obligation
#. Run the list-view action **Process Pending Regenerations** (from the
   base module) to actually rebuild the draft schedule for all flagged
   obligations; already-posted entries are always preserved and skipped
#. Alternatively, install ``account_perf_obligation_auto_schedule`` to
   have flagged obligations processed automatically and asynchronously
#. The **Generate Schedule Entries** button can still be used to force
   regeneration of the drafts on demand for a single obligation

Extensibility
=============

To implement a different recognition formula:

#. Extend the ``recognition_at_date_method`` selection field on ``perf.obligation``
   to add a new key (e.g. ``"monthly"``)
#. Implement the corresponding
   ``_compute_amount_to_recognize_monthly(date)`` method on the same model
#. Override ``_supports_schedule()`` and ``_get_schedule_dates()``
   if the new method should support schedule generation
#. Override ``_get_schedule_start_date()`` if the schedule start date
   needs additional constraints beyond start date and last posted entry

To make additional fields flag the obligation when modified, override
``_get_schedule_regenerate_trigger_fields()`` and add the field names
to the returned list. This module already adds ``start_date`` and
``end_date`` to the base list.
