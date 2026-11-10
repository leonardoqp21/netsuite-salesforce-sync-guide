# Typical errors in a NetSuite and Salesforce sync

Messages change and a vague one can fit several causes. Use this as **where to look first**.

```bash
python scripts/error_triage.py "INVALID_KEY_OR_REF: Invalid item reference key 99999"
python scripts/error_triage.py --file samples/errors.txt
```

## NetSuite side

| Message or symptom | Likely cause | First thing to check |
|---|---|---|
| `SSS_REQUEST_LIMIT_EXCEEDED`, "request limit exceeded" | NetSuite caps concurrent requests for the whole account. Other integrations share the pool | Set the Stacksync integration's **Concurrency Limit to 3**. Look at Integration Governance for slots in use |
| `INVALID_KEY_OR_REF` | A reference does not exist or is not allowed: an item, customer, subsidiary or term | The internal id in your mapping. Is the item active and available for this subsidiary? Does the customer exist yet? |
| `INVALID_FLD_VALUE` | A value is not valid for the field | The allowed list or format. Add it to the value map |
| "Please enter value(s) for ..." | A required field was not sent (terms, subsidiary, entity, an item) | Add a default or map it. Require it in Salesforce |
| Posting period closed | The transaction date is in a closed accounting period | Use a date in an open period, or ask Finance. Do not retry unchanged |
| `INSUFFICIENT_PERMISSION` | The integration role cannot do this on this record type | The role's permissions for the record and its sublists. Do not use an administrator role |
| `RCRD_HAS_BEEN_CHANGED` | The record changed between read and write | Retry. A retry reads current values again. If it repeats, look for another integration |
| Authentication errors | Token-based authentication or the integration record | Reconnect through the secure link. Never paste tokens into a chat |
| Currency or subsidiary not allowed | A combination is not valid | The customer's and the transaction's subsidiary and currencies |
| An item cannot be added to an order | The item is inactive or not available | The item in NetSuite |
| A sales order edit is refused | The order was fulfilled or billed | Process: new order, credit memo or a manual change |

## Salesforce side

| Message or symptom | Likely cause | First thing to check |
|---|---|---|
| `REQUEST_LIMIT_EXCEEDED: TotalRequests...` | The daily API allocation is used up. It is shared by every integration | API usage, and who else calls the API. Lower sync frequency and the per-app rate limit |
| `REQUEST_LIMIT_EXCEEDED: Concurrent...` | Too many long-running requests at once | Concurrency and batch sizes |
| `UNABLE_TO_LOCK_ROW` | Parallel writes to the same record or parent | Reduce parallel writes to related records. Retry |
| `Too many SOQL queries`, `Apex CPU time limit` | Salesforce automation fired by the write ran out of its own limits. Not an API limit | Triggers and flows on the written object. Smaller batches |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION`, `REQUIRED_FIELD_MISSING` | A validation rule or required field rejected the value | Fix the data or the rule. Retrying will not help |
| `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` | A value is not in a restricted picklist | The value map |
| `INSUFFICIENT_ACCESS`, field not visible | The connected user cannot see or write a custom field | The profile and field-level security |
| "The REST API is not enabled for this Organization" | The edition does not include the API | Edition, and API Enabled on the connected user |

## The bridge between them

| Symptom | Likely cause | First thing to check |
|---|---|---|
| An order never appears in NetSuite | Its customer is not in NetSuite yet, so the order is held back | The customer pair and the account's NetSuite id |
| Orders created with no lines | The array was empty or not built | The mapping table and the view |
| Lines missing after an edit | A partial array was sent | Always send the complete array |
| Customers twice | They existed in both systems before the first run, or a sync was recreated | [Matching and the first run](matching-and-initial-load.md) |
| A custom field is not in the mapping | It is not visible to the connected user, or not in the schema | Field-level security. A saved search with no rows may not show its columns |
| Late changes | The sync frequency or the per-app rate limit spaces out calls. Pending changes keep growing | Both settings |
| Paused sync | Errors from an app stopped it | The issues. Fix the cause, then switch it on |

## Sort the errors

1. Read the issue, not the symptom.
2. Group failures by cause.
3. Decide the resolution **per group**: retry re-reads the current source values, revert changes data in the other app, ignore leaves it.
4. Fix the **cause** in the source of truth before retrying.

## Concurrency, on both sides

NetSuite caps concurrent requests per account by service tier, and REST and SOAP share the cap. Stacksync never sends more than 3 at once, and in NetSuite you set the integration's Concurrency Limit so others keep room. On the Salesforce side, daily and concurrent limits are shared too. When both are tight, lower the per-app rate limit and the sync frequency, and run big loads off-peak.
