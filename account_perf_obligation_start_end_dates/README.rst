==================================================
Performance Obligations - Start/End Dates
==================================================

Extends the **Performance Obligations (IFRS 15)** module to support
time-based income and expense recognition using start and end dates.

Purpose
=======

When a performance obligation spans a defined period, this module computes
the amount to recognize at any given date using the **daily pro-rata** method.

It also provides the date range needed for **forecast generation**:
the **Generate Forecast Entries** button (from the base module) generates
draft recognition entries for each remaining month-end until the end date,
skipping periods already covered by posted entries or in the past.

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
#. Use the **Generate Forecast Entries** button to create draft
   recognition entries for each future month-end until the end date;
   already-posted entries and past periods are preserved and skipped;
   calling the button again replaces existing drafts

Extensibility
=============

To implement a different recognition formula:

#. Extend the ``recognition_at_date_method`` selection field on ``perf.obligation``
   to add a new key (e.g. ``"monthly"``)
#. Implement the corresponding
   ``_compute_amount_to_recognize_monthly(date)`` method on the same model
#. Override ``_supports_forecast()`` and ``_get_forecast_dates()``
   if the new method should support forecast generation
#. Override ``_get_forecast_start_date()`` to further constrain the
   forecast start date (e.g. to respect a start date field)
