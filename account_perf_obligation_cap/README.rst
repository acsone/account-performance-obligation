=============================================
Performance Obligations - Recognition Cap
=============================================

Extends the **Performance Obligations (IFRS 15)** module to allow a
maximum cumulative recognition amount (a *cap*) to be defined on a
performance obligation.

Purpose
=======

In some business situations the amount that can be recognized at any
given point in time must be restricted, independently of the recognition
method (daily pro-rata, manual, etc.). Typical cases include:

- revenue recognition limited by a contractual milestone;
- a cap agreed with the client pending final acceptance;
- a temporary limit while a dispute is ongoing.

The cap also supports **negative obligations** (revenue reversals,
credit notes): the cap amount must carry the same sign as the total
amount, and the comparison is always done on absolute values.

Features
========

- A **checkbox** *Limit Maximum Amount to Recognize* on the obligation.
- A **monetary field** *Maximum Amount Allowed for Recognition*, visible
  when the checkbox is ticked.
- A **Capped** filter in the list search bar to quickly find all
  obligations with an active cap.
- **Manual recognition guard**: the *Recognize Income/Expense* wizard
  raises a validation error if the entered amount exceeds the cap
  (in absolute terms).
- **Automatic schedule cap enforcement**:

  - entries below the cap are generated normally;
  - the entry that would first cross the cap is reduced to land exactly
    on it;
  - no entries are generated for subsequent periods;
  - if the cap is set *below* the already-recognized amount, the next
    entry is a **de-recognition** that brings the balance back to the cap.

Usage
=====

On the **Performance Obligation** form, tick *Limit Maximum Amount to
Recognize* and enter the cap amount. Odoo flags the obligation for
schedule regeneration. If ``account_perf_obligation_auto_schedule`` is
installed the job runs in the background; otherwise use the **Process
Pending Regenerations** list-view action.

Use the **Capped** filter in the list view to find all obligations with
an active cap.
