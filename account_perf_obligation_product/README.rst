===============================================
Performance Obligations - Product Configuration
===============================================

Configure automatic performance obligation creation on products.

Purpose
=======

This module adds a configuration tab to the product form that controls
whether a **Performance Obligation** (IFRS 15) should be automatically
created.

It is a pure configuration module: it adds fields to ``product.template``
and exposes them in the UI, but contains no sale-specific logic.
The actual obligation creation is handled by other modules, such as
``account_perf_obligation_sale``.

Features
========

- A dedicated **Revenue/Expense Recognition** tab on the product form.
- A **Auto-create Performance Obligation** checkbox that enables
  automatic obligation creation for the product.
- A **Revenue/Expense Recognition Duration** selection field (visible
  and required when the checkbox is ticked):

  - **At once** (``at_once``): the obligation
    covers a single day. The full amount is recognized immediately.
  - **Over several months** (``months``): the obligation spans a
    period ending a configurable number of months.

- A **Recognition Duration (months)** integer field (visible and
  required when the ``months`` method is selected). Must be a strictly
  positive integer.

Configuration
=============

No module-level configuration is required. All settings are per-product.

Usage
=====

#. Go to **Inventory** (or **Sales**) **> Products > Products**
#. Open a product form and navigate to the
   **Revenue/Expense Recognition** tab
#. Tick **Auto-create Performance Obligation**
#. Select a **Revenue/Expense Recognition Duration** method:

   - Choose **At once** for products that
     must be recognized entirely on the sale date (e.g. one-off services).
   - Choose **Over several months** for products spread over a
     known number of months. Enter the number of months in the
     **Recognition Duration (months)** field that appears below.

Once configured, install ``account_perf_obligation_sale`` to have
obligations created automatically when sale orders are confirmed.
