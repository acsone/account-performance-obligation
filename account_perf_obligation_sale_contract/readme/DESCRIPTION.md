This is a bridge module between
[account_perf_obligation_sale](../account_perf_obligation_sale),
[account_perf_obligation_contract](../account_perf_obligation_contract),
and `product_contract`.

When a sale order line for a contract product with *Auto-create Performance
Obligation* enabled is confirmed, a performance obligation is created and
linked to that line. When a contract line is subsequently created from that
sale order line, the existing obligation is **transferred** to the contract
line — no duplicate is created, and the link to the sale order line is removed.
The obligation's dates are then updated to match the contract line's
`date_start` and `date_end`.

For products configured both as contract products and for automatic obligation
creation, the recognition method, months duration, and days duration fields
are hidden on the product form and not required — the contract line dates take
precedence. The validation that normally enforces a recognition method on
non-contract products is bypassed for contract products.
