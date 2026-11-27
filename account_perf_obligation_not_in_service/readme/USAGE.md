1. Create or open a performance obligation with a recognition period (start and
   end dates).
2. Check *Not in Service* while the service has not started yet (you can also
   filter obligations using the *Not in Service* search filter).
3. When running recognition posting up to a given date, obligations still marked
   as *Not in Service* with a start date on or before that date are skipped for
   posting; their start date is moved to the first day of the following month
   and their schedule is regenerated. Attempting to manually post a recognition
   entry for an obligation not in service raises an error.
4. Uncheck *Not in Service* once the service actually starts so normal
   recognition entries can be posted.
