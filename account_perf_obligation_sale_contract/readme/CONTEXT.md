## Why this module?

`account_perf_obligation_sale` creates obligations when a sale order is
confirmed. `account_perf_obligation_contract` creates obligations when a
contract line is configured for auto-creation. For contract products, both
modules would independently create an obligation — resulting in duplicates.

This bridge module prevents that by transferring the obligation created at
sale order confirmation to the contract line when it is generated, so the
obligation's lifecycle is ultimately governed by the contract line dates.

It also relaxes the product-level validation: non-contract products with
auto-create enabled must have a recognition method, but contract products
are exempt since their dates come from the contract line.

## Companion modules

- **account_perf_obligation** *(required)*
- **account_perf_obligation_start_end_dates** *(required)*
- **account_perf_obligation_sale** *(required)*
- **account_perf_obligation_contract** *(required)*
- **product_contract** *(required)*
- **account_perf_obligation_auto_schedule** *(optional)*: automatically
  processes flagged obligations in the background.
