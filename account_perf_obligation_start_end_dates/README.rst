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
#. Use the **Generate Schedule Entries** button to create draft
   recognition entries for each month-end until the end date;
   already-posted entries are preserved and skipped;
   calling the button again replaces existing drafts

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
