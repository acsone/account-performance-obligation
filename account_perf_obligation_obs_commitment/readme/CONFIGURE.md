## Prerequisites

The user must belong to the **Show Full Accounting Features** group to access
the configuration settings.

## Settings

Go to *Invoicing > Configuration > Settings*, under the **Performance
Obligations** section, and fill in the four fields under
**Off-Balance Sheet Commitments**:

- **Off-Balance Sheet Journal**: a *General* type journal dedicated to
  off-balance sheet entries. Create one if needed (e.g. *Off-Balance Sheet*).
- **Off-Balance Sheet Commitment Income Account**: the account debited when an
  income obligation commitment is recorded or increased. Must be of type
  *Off-Balance Sheet*.
- **Off-Balance Sheet Commitment Expense Account**: the account debited when an
  expense obligation commitment is recorded or increased. Must be of type
  *Off-Balance Sheet*.
- **Off-Balance Sheet Commitment Counterpart Account**: the contra-account
  used as the offsetting leg whenever a commitment is recorded or adjusted.
  Must be of type *Off-Balance Sheet*.

All four fields are required per company. The adjustment action raises an
error for any obligation whose company is missing one of them.
