# Field mapping: Salesforce to NetSuite

These are **standard names**. Your connection's live fields, including custom ones, are the source of truth. Read them with `connections_tables` (or in the sync setup) and never guess a name.

## Account to Customer

| Salesforce | NetSuite | Owner | Notes |
|---|---|---|---|
| `Id` | `externalId` | Salesforce | Store the Salesforce id on the NetSuite customer so either side can find the other |
| `NetSuite_Internal_ID__c` (custom) | `internalId` | NetSuite | **The match key.** The ERP assigns it. Salesforce stores it |
| `Name` | `companyName` | NetSuite, once created | The legal name belongs to finance |
| `Phone`, `Website` | `phone`, `url` | Salesforce | Sales keeps them current |
| Billing address | Address book entries | NetSuite, once created | Address structures differ. Test them |
| `OwnerId` | `salesRep` | Salesforce | Ids differ. You need a mapping table |
| Payment terms (custom) | `terms` | NetSuite | A picklist on both sides. Needs a value map |
| Credit limit (custom) | `creditLimit` | NetSuite | Finance owns it. Sales only reads |
| Currency (custom) | `currency` | NetSuite | Set once |
| Selling entity (custom) | `subsidiary` | NetSuite | A OneWorld concept. Setting it on a customer works. Writes to subsidiary records themselves are listed as coming soon |

## Contact to Contact

| Salesforce | NetSuite | Notes |
|---|---|---|
| `Email` | `email` | Match key candidate for contacts |
| `FirstName`, `LastName` | `firstName`, `lastName` | |
| `AccountId` | `company` | A reference. Needs the customer to exist first |

## Opportunity or Order to Sales Order (header)

| Salesforce | NetSuite | Notes |
|---|---|---|
| `Id` | `externalId` | **The match key.** Also makes a retried create safe to repeat |
| `AccountId` (through the mapping) | `entity` | The **NetSuite customer internal id**. The customer must exist |
| `EffectiveDate` | `tranDate` | Must fall in an **open** accounting period |
| `PoNumber` | `otherRefNum` | The customer's purchase order |
| `CurrencyIsoCode` | `currency` | Must be allowed for the customer and subsidiary |
| `Status` | `status` | Direction depends on your process. Often NetSuite to Salesforce |
| Order lines | `itemList` | See [order lines](order-lines.md) |

## Product to Item

| Salesforce | NetSuite | Notes |
|---|---|---|
| `ProductCode` | item name or a custom field | The **mapping table** between product code and item internal id is the heart of order sync |
| `Name` | `displayName` | |
| `IsActive` | `isInactive` (inverted) | An **inactive item cannot be added** to a new transaction |
| List price | Price level | Price books and price levels are different models. Decide the source of price |

## Invoice and Payment to Salesforce

NetSuite invoices and customer payments are created in the ERP. In Salesforce they usually land in custom objects or a custom field summary, **read only**. Map the invoice number, date, amount, status, due date and amount remaining.

## IDs: the part people get wrong

| ID | Lives in | Why |
|---|---|---|
| NetSuite internal id | A Salesforce custom field | The reliable match key |
| Salesforce id | NetSuite `externalId` | So NetSuite can point back, and a retry cannot create a second record |
| Product code to item id | A mapping table | Orders need item internal ids |
| Owner ids | A mapping table | Sales rep in NetSuite, owner in Salesforce |

## Required fields

NetSuite requires fields that Salesforce may not have, for example payment terms or subsidiary on a customer. Give them **defaults** and map the values. Make the matching field **required in Salesforce** so it is never empty.

## Picklists

Payment terms, order status, currency, country and industry lists differ. **Every value needs a counterpart**, and you need a rule for values that have none. [`scripts/ownership_check.py`](../scripts/ownership_check.py) flags a picklist without a value map.

## Check your own

```bash
python scripts/ownership_check.py ownership.example.json
```

The example matrix has 12 fields across customers and orders.
