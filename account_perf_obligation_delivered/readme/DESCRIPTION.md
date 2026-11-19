This module adds a recognition method for performance obligations whose
revenue (or expense) cannot be spread linearly between two dates, typically
products invoiced on consumption.

With the *Delivered Amount + Projected Balance* method:

* a **delivered amount** (lower than or equal to the total amount) is
  recognized as soon as it is known, without being spread;
* the remaining balance is only **projected** with draft entries, spread
  until the end date, and is never posted until it becomes delivered amount;
* the start date is not required, the end date is.
