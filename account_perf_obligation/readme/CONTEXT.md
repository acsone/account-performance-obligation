## Why this module?

IFRS 15 requires income (and symmetrically, expenses) to be recognized when
performance obligations are satisfied — regardless of when invoicing occurs.

In practice, a company may invoice a customer upfront for a service delivered
over several months. Standard Odoo records the revenue at invoicing time, which
does not comply with IFRS 15. This module bridges that gap by introducing a
**Performance Obligation** object that decouples invoicing from recognition.

## Who is this for?

- Accountants and finance teams working under IFRS 15 (or similar standards
  such as ASC 606).
- Companies recognizing revenue or expenses over time: subscriptions,
  long-term contracts, prepaid services, etc.

## Companion module

For high-volume installations, install `account_perf_obligation_auto_schedule`
to have flagged obligations processed asynchronously via `queue_job`, without
any manual intervention.
