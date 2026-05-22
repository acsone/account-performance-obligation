## Manual adjustment

Go to *Invoicing > Accounting > Adjust Off-Balance Sheet Commitments* to open
the adjustment wizard. Enter the reference date and click **Adjust**.

Odoo checks each obligation: if the commitment account balance (A) no longer
matches the remaining obligation — total amount minus recognized P&L up to the
chosen date (B) — an adjustment entry is posted at that date:

- **A > B** (more recognized than the balance reflects): credit the commitment
  account, debit the counterpart account.
- **A < B** (balance fell below expected): debit the commitment account, credit
  the counterpart account.

The wizard is typically run at month-end, after the recognition entries for the
period have been posted.
