==================================================
Performance Obligations - Start/End Dates
==================================================

Extends the **Performance Obligations (IFRS 15)** module to support
time-based income and expense recognition using start and end dates.

Purpose
=======

When a performance obligation spans a defined period, this module computes
the amount to recognize at any given date using the **daily pro-rata** method
and provides the date range needed for schedule generation.

Draft recognition entries are generated for each month-end from start date
to end date, skipping periods already covered by posted entries. If the end
date is shortened to before the last posted entry, a single corrective draft
entry is generated at the end of the current month (or at the last posted
date if that is further in the future) to unwind the excess without amending
already-posted entries.

Changes to **start date** or **end date** flag the obligation for schedule
regeneration via ``schedule_needs_regeneration``, in addition to the triggers
already handled by the base module (total amount, recognition method, linked
journal items).

The architecture is designed so that alternative computation methods
(e.g. full-month based) can be easily added by extending the selection
field and implementing the corresponding method.

Usage
=====

#. On a performance obligation, select a **Recognition at Date Method**
   (e.g. "Daily Pro-Rata") and fill in the **Start Date** and **End Date**
   (these fields become required when the daily pro-rata method is selected)
#. When opening the **Recognize Income/Expense** wizard, the
   **Amount to Recognize** field is automatically pre-filled based on
   the selected date and the obligation period, but can be modified
   before confirmation
#. Changes to dates, total amount, recognition method or linked journal
   items automatically flag the obligation for schedule regeneration
#. Run the list-view action **Process Pending Regenerations** (from the
   base module) to rebuild the draft schedule for all flagged obligations,
   or use the **Generate Schedule Entries** button on a single obligation
#. Alternatively, install ``account_perf_obligation_auto_schedule`` to
   have flagged obligations processed automatically and asynchronously

Extensibility
=============

To implement a different recognition formula:

#. Extend the ``recognition_at_date_method`` selection field on ``perf.obligation``
   to add a new key (e.g. ``"monthly"``)
#. Implement the corresponding
   ``_compute_amount_to_recognize_monthly(date)`` method on the same model
#. Override ``_supports_schedule()`` and ``_get_schedule_dates()``
   if the new method should support schedule generation
#. Override ``_get_schedule_start_date()`` or ``_get_schedule_end_date()``
   if the schedule boundaries need additional constraints

To make additional fields flag the obligation when modified, override
``_get_recognition_trigger_fields()`` and add the field names
to the returned list. This module already adds ``start_date`` and
``end_date`` to the base list.
