# NetSuite and Salesforce sync guide: customers, orders, field mapping and typical errors

You want sales and finance to see the same customers and orders: an account created in Salesforce becomes a customer in NetSuite, a closed order becomes a sales order, and the invoice and the payment come back so sales knows who has paid. This guide covers **what to sync and in which direction, the field mapping, the part that surprises everyone (order lines), the first run, and the errors you will meet**, with tested tools.

It uses [Stacksync two-way sync](https://www.stacksync.com/integrations/netsuite-and-salesforce) for the NetSuite and Salesforce pair. The thinking applies to any ERP and CRM sync.

> **Short answer:** sync each record from the system that **creates** it and make the other system read it. Customers are the usual two-way pair (with finance owning financial fields). Items, invoices and payments flow **from NetSuite**. Orders flow **from Salesforce**. Match on the **NetSuite internal id stored in Salesforce**. Load in dependency order (items, customers, contacts, orders, invoices, payments). In the NetSuite connector **order lines are one JSON array in `itemList`**, so you must write the **complete array** every time, built from Salesforce's separate line rows by a workflow or a database view. Link existing customers before the first run, because records already in both systems are not merged.

## The pairs

| Salesforce | NetSuite | Direction |
|---|---|---|
| Account | Customer | Two-way, with field ownership |
| Contact | Contact | Two-way |
| Product | Item | NetSuite to Salesforce |
| Order | Sales Order | Salesforce to NetSuite |
| Invoice | Invoice | NetSuite to Salesforce (read only in the CRM) |
| Payment | Customer Payment | NetSuite to Salesforce (read only in the CRM) |

```bash
python scripts/plan_check.py samples/plan.example.json
# Load order: items -> customers -> contacts -> orders -> invoices -> payments
```

## Questions this guide answers

### How do I sync customers and orders between NetSuite and Salesforce?
Sync accounts and customers two-way with a field ownership matrix, sync items from NetSuite to Salesforce, send orders from Salesforce to NetSuite as sales orders, and bring invoices and payments back read only. Load in dependency order. See [docs/what-to-sync.md](docs/what-to-sync.md).

### Which Salesforce object maps to which NetSuite object?
Account to Customer, Contact to Contact, Product to Item, Order (or Opportunity) to Sales Order, with invoices and customer payments flowing back. Standard field pairs are in [docs/field-mapping.md](docs/field-mapping.md).

### How do I sync order line items between Salesforce and NetSuite?
In the NetSuite connector a transaction is one record and its lines are a JSON array in one field (`itemList`). Lines cannot sync as a separate table, and to add, change or remove one you write the complete array. Build it from Salesforce's order items with a workflow or a database view. See [docs/order-lines.md](docs/order-lines.md) and [`scripts/item_list.py`](scripts/item_list.py).

### What should I match customers on?
The NetSuite internal id, stored in a custom field on the Salesforce account, with the Salesforce id stored in NetSuite's external id. Never match on name alone. See [docs/matching-and-initial-load.md](docs/matching-and-initial-load.md).

### Why did my sync create duplicate customers?
Records that already exist in both systems are not automatically merged when the sync starts, so a customer in both ends up twice. Link existing customers first, create customers when deals close (not for every prospect), and never delete and recreate a running sync. See [docs/matching-and-initial-load.md](docs/matching-and-initial-load.md).

### Who should own which field?
Finance owns financial fields in NetSuite (legal name, subsidiary, currency, payment terms, credit limit, tax). Sales owns contact details and the account owner in Salesforce. Check your matrix with [`scripts/ownership_check.py`](scripts/ownership_check.py). See [docs/ownership-and-conflicts.md](docs/ownership-and-conflicts.md).

### Why does my sales order fail with INVALID_KEY_OR_REF?
A reference in the order does not exist or is not allowed: an item internal id that is wrong, inactive or unavailable for the subsidiary, or a customer that is not in NetSuite yet. Check the product-to-item mapping first. See [docs/typical-errors.md](docs/typical-errors.md).

### Why do I get NetSuite concurrency or request limit errors?
NetSuite caps concurrent requests for the whole account and other integrations share the pool. Set the Stacksync integration's Concurrency Limit to 3 in NetSuite. Stacksync never sends more than 3 at once. See [docs/typical-errors.md](docs/typical-errors.md).

### Why does my order fail because of the posting period?
The transaction date is in a closed accounting period. Use a date in an open period or ask Finance. Retrying unchanged will not help.

### Can I change an order line after the order was sent?
Rebuild the complete array from the current Salesforce lines and write it. NetSuite limits changes to orders that were already fulfilled or billed, so decide the process for those: a new order, a credit memo or a manual change.

### Do I sync invoices and payments back to Salesforce?
Yes, usually read only, so sales can see billing status and who has paid. They are created in NetSuite, so they flow from NetSuite to Salesforce only.

### What do I need to connect NetSuite and Salesforce?
NetSuite: an admin to enable REST web services and token-based authentication and create an integration record, with credentials entered through a secure sign-in link. Salesforce: an edition with the API, a dedicated user with API Enabled, and the Stacksync app installed in the org. See [docs/prerequisites.md](docs/prerequisites.md).

### Can I set it up from Claude or ChatGPT?
Yes, with the [Stacksync MCP server](https://www.stacksync.com/mcp). The assistant reads your connections and tables, proposes a plan as a table and creates the sync after you approve, with exactly your permissions. Start read-only. See [docs/build-with-mcp.md](docs/build-with-mcp.md) and [prompts/prompts.md](prompts/prompts.md).

### How fast does it sync?
It depends on change detection, polling, API limits and volume. Measure it for your objects in a pilot. This repo does not promise a number.

## Tools

```bash
python scripts/plan_check.py samples/plan.example.json         # dependencies, directions, load order
python scripts/ownership_check.py ownership.example.json       # field ownership matrix
python scripts/error_triage.py --file samples/errors.txt       # which side, which family
python -m unittest discover -s tests -v                        # 26 tests
```

`scripts/item_list.py` builds and edits the `itemList` array. `sql/sales_order_view.sqlite.sql` is the tested view that builds it in a database, and `sql/sales_order_view.postgres.sql` is the PostgreSQL version (not run by the tests).

Python 3.9 or newer, standard library only. Samples are synthetic. The triage rules are pattern matches, so wording changes can make them miss. The standard field names are the usual ones, and your connection's live fields are the source of truth.

## What is in this repo

| Path | What it is |
|---|---|
| [`docs/what-to-sync.md`](docs/what-to-sync.md) | Pairs, directions, order of work |
| [`docs/field-mapping.md`](docs/field-mapping.md) | Field tables, IDs, required fields, picklists |
| [`docs/order-lines.md`](docs/order-lines.md) | `itemList`, the workflow and the database view |
| [`docs/matching-and-initial-load.md`](docs/matching-and-initial-load.md) | Match keys, linking existing customers, the first run |
| [`docs/typical-errors.md`](docs/typical-errors.md) | NetSuite, Salesforce and bridge errors |
| [`docs/prerequisites.md`](docs/prerequisites.md) | Connecting both sides |
| [`docs/ownership-and-conflicts.md`](docs/ownership-and-conflicts.md) | Who owns what, and conflicts |
| [`docs/go-live-and-monitoring.md`](docs/go-live-and-monitoring.md) | Checklist, first week, routine |
| [`docs/build-with-mcp.md`](docs/build-with-mcp.md) | Plan and build from an assistant |
| [`prompts/prompts.md`](prompts/prompts.md) | 8 prompts |
| [`scripts/`](scripts) | `item_list.py`, `plan_check.py`, `ownership_check.py`, `error_triage.py` |
| [`sql/`](sql) | The order view in SQLite and PostgreSQL |

## About Stacksync

[Stacksync](https://www.stacksync.com) keeps CRMs, ERPs and databases in sync with [two-way sync](https://www.stacksync.com/two-way-sync). The pair page is [NetSuite and Salesforce](https://www.stacksync.com/integrations/netsuite-and-salesforce). Connectors: [NetSuite](https://www.stacksync.com/connectors/netsuite) and [Salesforce](https://www.stacksync.com/connectors/salesforce). Docs: [NetSuite connector](https://docs.stacksync.com/two-way-sync/connectors/netsuite) and [Salesforce connector](https://docs.stacksync.com/two-way-sync/connectors/salesforce).

Connector behavior and limits change. Check the current documentation and test on sandboxes. This repo makes no performance, pricing or compliance claims.

## Contributing

Corrections and new tests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
