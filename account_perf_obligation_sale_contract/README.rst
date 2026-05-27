=========================================
Performance Obligations - Sale & Contract
=========================================

Bridge module between `account_perf_obligation_sale`,
`account_perf_obligation_contract` and `product_contract`.

When a sale order line for a contract product is confirmed, a performance
obligation is created and linked to the sale order line. When a contract
line is subsequently created from that sale order line, the existing
obligation is transferred to the contract line — no duplicate is created,
and the link to the sale order line is removed. The obligation dates are
then driven by the contract line dates rather than the product's recognition
method configuration.

When a product is configured both as a contract product (``is_contract``
enabled) and for automatic obligation creation
(``perf_obligation_sale_auto_create`` enabled), the recognition method,
months duration and days duration fields on the product are ignored — the
contract line dates take precedence. No recognition method needs to be set
on such products.

Usage
=====

From a sale order
-----------------

#. Confirm a sale order containing a contract product configured for
   automatic obligation creation (``perf_obligation_sale_auto_create``
   enabled on the product). A performance obligation is created and linked
   to the contract line.
#. Create the contract from the sale order (via **Create Contracts**). The
   existing performance obligation is automatically transferred to the new
   contract line and unlinked from the sale order line.
