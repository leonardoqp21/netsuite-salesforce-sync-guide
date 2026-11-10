# Go live and keep it healthy

## Before go-live

- [ ] Plan checked: `python scripts/plan_check.py plan.json`
- [ ] Ownership matrix reviewed with sales **and** finance: `python scripts/ownership_check.py matrix.json`
- [ ] Mapping tables built and reviewed: product codes to item ids, owner ids, every picklist
- [ ] Existing customers **linked** (NetSuite internal id in Salesforce) and duplicates cleaned
- [ ] Prospects excluded. Customers are created when deals close
- [ ] Required NetSuite fields have defaults
- [ ] NetSuite integration role limited. Concurrency Limit set to 3
- [ ] Salesforce user dedicated, with API Enabled, custom fields visible
- [ ] Delete Protection decided for each app
- [ ] Sandbox rehearsal done. Totals agree. Nothing written to a closed period
- [ ] A conflict test written down for every "both" field
- [ ] A rollback plan: pause the sync (paused changes wait), and a backup of both systems

## The first week

| When | Do |
|---|---|
| Day 1 | Start with customers and items only. Watch the issues list |
| Day 2 to 3 | Add orders for one product line. Check ten orders line by line |
| Day 4 to 5 | Add invoices and payments. Compare totals |
| End of week | Count records on both sides per object. Review all issues |

Do not switch everything on at once.

## What to watch

| Signal | Why |
|---|---|
| **Issues** | Failed records. Fix causes, do not only retry |
| **Pending changes** | Growing means changes arrive faster than the pace you set |
| **Record counts** on both sides | A doubled count is the first sign of duplicates |
| **Orders held back** | Orders waiting for a customer to exist |
| **NetSuite Integration Governance** | Concurrency slots in use |
| **Salesforce API usage, last 24 hours** | The daily allocation is shared |
| **A paused sync** | App errors can stop it |
| **Totals** (orders in Salesforce vs sales orders in NetSuite, per day) | The reconciliation that matters |

## Weekly routine

1. Group issues by cause with `scripts/error_triage.py`.
2. Compare order counts and totals between systems.
3. Check for new duplicates after imports.
4. Review what changed: a new field, a new picklist value, a new automation, a new item.

## Rules that keep it safe

- **Edit the sync. Never delete and recreate it.** A new sync does not know which records the old one linked.
- **Send the complete table-pair list** whenever you change a sync. A pair left out is removed, with its record links and issues.
- **Pause instead of delete** when you want it stopped. Paused changes wait.
- **Before turning Delete Protection off,** read the held-delete count.
- **Choose the resolution for each group of issues.** Retry, revert and ignore change data in different apps.
- **Add a new item to the mapping table before** it is sold.

## Pace

If you see rate-limit or concurrency errors, set a per-app rate limit on each side (per second or per minute), choose the slowest Data Sync Frequency the business accepts, and run big loads off-peak. A per-second limit protects against bursts. It does not cap a daily total.

## Backups

A sync is not a backup. Keep backups of both systems.
