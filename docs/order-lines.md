# Order lines: the part that surprises everyone

In Salesforce, an order's lines are **separate rows** (order items, or opportunity products). In the NetSuite connector, a transaction is **one record**, and its lines are a **JSON array inside one field**.

## The NetSuite shape

```json
[
  { "item": { "internalId": "38704" }, "quantity": 2, "rate": 10.0, "line": 1 },
  { "item": { "internalId": "38705" }, "quantity": 1, "rate": 25.0, "line": 2 }
]
```

The field is `itemList` for most transactions, and `lineList` for journal entries.

## The rules

1. **Lines cannot sync as a separate table.** NetSuite accepts line changes only through the whole transaction, header and all lines.
2. **To add, change or remove a line, write the complete updated array.** Stacksync sends the whole transaction to NetSuite. Never send only the changed line.
3. **A database or workflow can split the array into rows for reading.** But changes meant for NetSuite go back into the array field.

So the work is a translation: many Salesforce rows become one array, and the array becomes rows again for reporting.

## Option A: a workflow builds the array

A workflow reacts to a new or changed order, reads its lines, looks up each product in the mapping table, builds the **complete** `itemList` and creates or updates the sales order. Good for low volume and for logic that is easier in code.

[`scripts/item_list.py`](../scripts/item_list.py) is that translation, tested:

```python
from item_list import build_item_list, change_line, remove_line

item_map = {"SKU-A": "38704", "SKU-B": "38705"}          # product code -> NetSuite item id
lines = build_item_list(order_items, item_map)          # the complete array
lines = change_line(lines, 2, quantity=3)               # still the complete array
```

It refuses to build a line for a product with no mapping, a zero quantity or a negative price, and the error names the line, so a person can fix the data.

## Option B: a database view builds the array

Sync Salesforce orders and order items into a database. A **view** joins them with the item mapping table and produces **one row per order with an `itemList` JSON array**. That view feeds the NetSuite sales order table.

```sql
SELECT o.id AS salesforce_order_id,
       a.netsuite_internal_id AS entity_internal_id,
       json_group_array(json_object(
         'item', json_object('internalId', m.netsuite_item_id),
         'quantity', oi.quantity, 'rate', oi.unit_price, 'line', oi.line_number)) AS item_list
...
WHERE a.netsuite_internal_id IS NOT NULL
```

- [`sql/sales_order_view.sqlite.sql`](../sql/sales_order_view.sqlite.sql) is tested in this repo.
- [`sql/sales_order_view.postgres.sql`](../sql/sales_order_view.postgres.sql) is the PostgreSQL version. **It is not run by this repo's tests.** Test it on your own data.
- A database view can supply data to the connected app but **cannot accept writes back**. That fits: orders flow from Salesforce to NetSuite.
- The `WHERE ... IS NOT NULL` keeps orders **back** until their customer exists in NetSuite.

Check with your connector's documentation that your database connector supports views as a source.

## Editing a line later

A salesperson changes a quantity on an order that was already sent:

1. Rebuild the **complete** array from the current Salesforce lines.
2. Write it to `itemList`. Stacksync sends the whole transaction.
3. Use `diff_item_lists(old, new)` to log what changed.

Be aware that NetSuite limits changes to transactions that have already been **fulfilled or billed**. A line edit on such an order may be refused. Decide the process: usually a new order, a credit memo or a manual change in NetSuite.

## Deleting a line

Remove it from the array and write the complete array. `remove_line` renumbers the rest. If Salesforce deleted the line, the rebuild drops it. Decide whether deleting lines in the CRM should be allowed once the order is in the ERP.

## What can go wrong

| Problem | Cause | Fix |
|---|---|---|
| `INVALID_KEY_OR_REF` on a line | An item internal id does not exist, is inactive or is not available for the subsidiary | Fix the mapping. Check the item in NetSuite |
| A line disappears | A partial array was sent | Always send the complete array |
| Wrong line order | No stable line number | Number lines from the source, in order |
| Rounding differences | Floating point | Use exact decimals. The builder does |
| A line for an unmapped product | No row in the mapping table | The builder stops and names the line. Add the mapping |
| Order total differs | Tax, discounts or price levels | Decide where price and tax are calculated, and compare totals |

## Price and tax

Decide **who calculates the price and the tax**. A common design: Salesforce sends quantity and the agreed unit price, NetSuite calculates tax. If both calculate, expect differences. Compare the order total on both sides during your sandbox test.

## Test it

```bash
python -m unittest discover -s tests -v
```

The tests build the array, refuse bad lines, round-trip it for reporting, change and remove lines returning the complete array, diff two versions and run the SQL view against an in-memory database.
