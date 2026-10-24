## Prerequisites

The user must belong to the **Show Full Accounting Features** group to access
the *Performance Obligations* smart button on the sale order and contract forms.

## Confirm a sale order

Confirm a sale order containing a contract product with *Auto-create
Performance Obligation* enabled.

By default (*Automatically Create Contracts At Sale Order Confirmation* is
enabled on the company), the contract and its lines are created immediately
at confirmation. In that case the performance obligation is created and linked
directly to the contract line, with dates matching the contract line's
`date_start` and `date_end`.

If automatic contract creation is disabled on the company, the obligation is
first linked to the sale order line. When the contract line is later created
from the sale order line (e.g. via **Create Contracts**), the obligation is
transferred to the contract line automatically — unlinked from the sale order
line and updated with the contract line dates. No duplicate is created.
