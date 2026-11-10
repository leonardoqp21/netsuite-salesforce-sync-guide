# Ownership and conflicts

Most conflicts are design problems. Two teams each believe they own a field. Decide **who owns each field** and the rest is simple.

## The principle

| Owner | Meaning | Direction |
|---|---|---|
| **NetSuite** | Finance or operations owns it. Salesforce displays it | NetSuite to Salesforce |
| **Salesforce** | Sales owns it. NetSuite receives it | Salesforce to NetSuite |
| **Both** | Either team may edit it. **This is where conflicts live** | Two-way, with a conflict plan |

An owner whose field flows back from the other system is not an owner.

## A starting point

| Area | Usually NetSuite | Usually Salesforce | Often both |
|---|---|---|---|
| **Customer** | Legal name, subsidiary, currency, payment terms, credit limit, tax | Phone, website, owner, segment | Billing email, contact details |
| **Orders** | Status, fulfillment, billing state | Header and lines until released | Almost never |
| **Items** | Everything | Nothing (read only) | Never |
| **Invoices, payments** | Everything | Nothing (read only) | Never |

Your teams decide. The runnable matrix is [`ownership.example.json`](../ownership.example.json), and it is checked by:

```bash
python scripts/ownership_check.py ownership.example.json
```

It fails when an owner's field flows the wrong way, when "both" has no conflict plan, when a picklist has no value map, when owner ids have no mapping table, when an object has no match key, and when order lines are made two-way.

## How to enforce it in the sync

- Direction is chosen **per table pair**, and a two-way table can hold fields that flow one direction. Use a **per-field direction** for fields one system owns.
- **Read-only fields** (record ids, formula fields, computed values) sync only **out of** the app that holds them.
- **Delete Protection** per app stops deletes made in the other app from reaching this one. Before you turn it off, read the held-delete count.

## What happens when both edit the same field?

It depends on how the sync is configured. Conflict handling can be set per object and per field in some configurations (for example, the most recent change wins, or system precedence), and Stacksync's guidance is to **test conflicting edits instead of assuming a policy**. So:

1. Make conflicts **rare**: ownership removes most of them.
2. For the few "both" fields, **write the plan** and **test it** in sandboxes: edit the same field in both within a minute and record the result.
3. Keep the result next to the matrix.

## Finance fields are special

Credit limit, payment terms, tax settings and subsidiary change how money moves. Make **NetSuite** the owner and Salesforce read only, so a salesperson cannot edit them in a CRM screen.

## Deletes

A customer with transactions cannot simply be deleted in NetSuite. Decide what a delete in Salesforce means (usually: nothing happens in NetSuite) and turn **Delete Protection** on for NetSuite.
