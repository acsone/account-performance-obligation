This module adds a *Not in Service* flag to performance obligations that
already have a recognition period (start and end dates).

Nothing is recognized for an obligation while it is marked as *Not in
Service*. When a recognition posting run reaches an open obligation that is
not in service and whose start date is on or before the posting date, its start
date is moved to the first day of the month following the posting date and its
schedule is regenerated if needed. Directly posting a recognition entry for an
obligation that is not in service is also blocked.

If postponing the start date would place it after the end date, posting is
blocked with an error unless the dates are adjusted or the obligation is put
in service. When the start date equals the end date, both dates are postponed;
otherwise the end date is kept.
