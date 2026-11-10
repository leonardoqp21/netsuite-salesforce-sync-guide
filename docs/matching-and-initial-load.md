# Matching and the first run

## The match key is an id, not a name

Match records by an **id that both systems store**, not by name. Names change, collide and differ.

| Object | Match on | Where it lives |
|---|---|---|
| Customer and Account | NetSuite **internal id** | A custom field on the Salesforce Account |
| Customer and Account (the other way) | The Salesforce id | NetSuite `externalId` |
| Sales order | The Salesforce order id | NetSuite `externalId` |
| Item and Product | A mapping table (product code to item id) | A table you maintain |
| Contact | Email, then an id | A custom field |

Store the **NetSuite internal id in Salesforce** and match on it. When a customer already exists in both systems, matching on the internal id is how you tell the sync they are the same record.

## What the first run does

When the sync starts, it copies the records that already exist in the sending app (in both apps for a two-way pair). Two things to know:

- **Records that already exist in both systems are not automatically merged.** A customer in both ends up twice on each side unless you link them first.
- **Existing records are backfilled** at the start. When you add a field later you choose whether to backfill it for existing records.

## Link the customers you already have

Most companies already have customers in both systems. Before the first run:

1. Export customers from NetSuite and accounts from Salesforce.
2. Match them: tax registration number first, then a normalized legal name, then website domain. Never merge on name alone.
3. For each match, write the **NetSuite internal id into the Salesforce account** (and the Salesforce id into NetSuite's external id).
4. Decide what to do with the rest: accounts with no customer (prospects, which should not sync yet) and customers with no account.
5. Clean duplicates inside each system first.

The approach is the same for any overlap check: normalize the keys (lowercase and trim emails and domains, strip punctuation from tax numbers, drop legal suffixes from names), match, and list what is in both, what is only in one, and what has no usable key.

## Prospects are not customers

A Salesforce account that has never bought has no NetSuite customer. **Do not sync every account to NetSuite.** Create the customer when a deal closes, not when an account is created. Otherwise the ERP fills with prospects and finance cleans it up by hand. A filter on the sync or a closed-won workflow decides when a customer is born.

## Load in order

```text
items -> customers -> contacts -> orders -> invoices -> payments
```

Run `python scripts/plan_check.py samples/plan.example.json` to verify your plan loads parents first.

## Rehearse on sandboxes

Try everything on a **Salesforce sandbox** and a **NetSuite sandbox account** with a slice of your data. Check:

- how many customers and orders were created on each side
- that no order was created for a customer that does not exist yet
- that totals agree
- that nothing was written to a closed period

## After the first run

- Count records on both sides per object. A doubled count is the first sign of duplicates.
- Spot check ten customers and ten orders line by line.
- Read the issues list before you trust it.

## If something duplicated

- **Do not delete and recreate the sync.** A new sync does not know which records the old one linked, so it duplicates every record again.
- Fix the overlap in one system and let the sync carry it.
- Edit the existing sync.
