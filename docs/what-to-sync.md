# What to sync between NetSuite and Salesforce, and in which direction

Salesforce is where **sales** works. NetSuite is where **finance and operations** work. A good sync respects that: each system owns what its team owns, and the other one reads it.

## The pairs

| Salesforce | NetSuite | Direction | Why |
|---|---|---|---|
| **Account** | **Customer** | Two-way, with field ownership | Sales creates the account. Finance owns the financial fields once the customer exists |
| **Contact** | **Contact** | Two-way, usually | Both teams keep people current |
| **Product** | **Item** | NetSuite to Salesforce | The ERP owns the item master. The CRM only needs to read it |
| **Order** (or Opportunity) | **Sales Order** | Salesforce to NetSuite | Orders start in the CRM and are fulfilled and billed in the ERP |
| Order status | Sales Order status | NetSuite to Salesforce | Operations moves the order forward. Sales wants to see where it is |
| **Invoice** | **Invoice** | NetSuite to Salesforce, read only in the CRM | Invoices are created in the ERP |
| **Payment** | **Customer Payment** | NetSuite to Salesforce, read only in the CRM | So sales can see who has paid |

Confirm the objects and directions your connection supports. Customers, contacts, vendors and many transactions (sales orders, invoices, purchase orders, journal entries, item fulfillments, vendor bills) read and write. Accounts, accounting periods, departments, classes and locations are read only for now, and saved searches are read only. Custom objects read, and writing them is on request. A readable object is not automatically writable.

## The rule behind the table

> **Sync a record from the system that creates it. Make the other system read it.**

Two-way is the exception, for records both teams genuinely edit (customers, contacts). Everything that starts in one system and is transformed in the other (orders, invoices, payments, items) flows one direction.

[`scripts/plan_check.py`](../scripts/plan_check.py) enforces it: invoices and payments must flow from NetSuite, items from NetSuite, and a two-way sales order must state how lines are handled.

## The order to build it

Records depend on each other. Load them in this order:

```text
items -> customers -> contacts -> orders -> invoices -> payments
```

An order needs its customer and its items to exist **in both systems** first. A plan check that fails on a child before its parent saves a bad first run:

```bash
python scripts/plan_check.py samples/plan.example.json
```

## What not to sync

- **Everything.** Sync the objects and fields a team uses. A smaller sync is easier to keep correct.
- **Financial postings** (journal entries, payments applied) back into the CRM beyond what sales needs to see.
- **Computed fields** such as formula fields as if they were editable.
- **Free-text notes** unless someone will read them on the other side.

## What about quotes and CPQ?

If you quote in Salesforce CPQ or another quoting tool, the line structure and the objects differ from standard Salesforce orders. This guide covers standard Salesforce objects. Treat CPQ objects as their own mapping exercise.

## Start small

1. Customers (one direction first if you are unsure).
2. Items.
3. Orders for one product line.
4. Add invoices and payments.
5. Add contacts and the rest.

Turning a table pair into two-way later is a smaller change than undoing unwanted writes.
