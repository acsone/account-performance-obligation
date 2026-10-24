This module extends [Performance Obligations (IFRS 15)](../account_perf_obligation)
to allow a **maximum cumulative recognition amount** (a *cap*) to be defined
on a performance obligation.

## Features

- A **checkbox** *Limit Maximum Amount to Recognize* on the obligation form.
- A **monetary field** *Maximum Amount Allowed for Recognition*, visible when
  the checkbox is ticked.
- A **Capped** filter in the list search bar to quickly find all obligations
  with an active cap.
- **Manual recognition guard**: the *Recognize Income/Expense* wizard raises
  a validation error if the entered amount exceeds the cap (in absolute terms).
- **Automatic schedule cap enforcement**:
  - entries below the cap are generated normally;
  - the entry that would first cross the cap is reduced to land exactly on it;
  - no entries are generated for subsequent periods;
  - if the cap is set *below* the already-recognized amount, the next entry
    is a de-recognition that brings the balance back to the cap.
- **Negative obligations** are supported: the cap amount must carry the same
  sign as the total amount; comparison is always done on absolute values.
