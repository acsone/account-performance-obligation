This module adds milestones to performance obligations using the daily
pro-rata recognition method.

A milestone is a date and a cumulative amount: the amount that must be
recognized at the end of that date. The obligation is recognized linearly up to
the amount of the first milestone, then linearly from one milestone to the
next, and finally linearly from the last milestone up to the total amount at
the end of the recognition period.

Milestone amounts must have the same sign as the total amount and cannot exceed
it. They may decrease from one milestone to the next (income can be
de-recognized). Milestones dated before the start date, or on or after the end
date (where the total amount is recognized), are ignored.
