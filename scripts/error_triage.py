"""Triage an error from a NetSuite and Salesforce sync: which side, which family, what to try first.

    python scripts/error_triage.py "INVALID_KEY_OR_REF: Invalid item reference key 99999"
    python scripts/error_triage.py --file samples/errors.txt

The rules are pattern matches on messages these systems commonly return. Wording changes, and a
vague message can fit more than one cause, so treat the answer as where to LOOK, not a diagnosis.
Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    side: str
    family: str
    pattern: re.Pattern
    meaning: str
    next_steps: tuple[str, ...]


def r(side, family, pattern, meaning, *steps):
    return Rule(side, family, re.compile(pattern, re.I), meaning, steps)


RULES: list[Rule] = [
    # ---- NetSuite
    r("netsuite", "concurrency", r"SSS_REQUEST_LIMIT_EXCEEDED|concurrent request|request limit exceeded",
      "NetSuite caps concurrent requests for the whole account. Other integrations share the pool.",
      "In NetSuite set the Stacksync integration's Concurrency Limit to 3 and size the others the same way",
      "Look at Integration Governance for the slots in use", "Retry after the limits are fixed"),
    r("netsuite", "bad-reference", r"INVALID_KEY_OR_REF|invalid .* reference|reference key",
      "A reference (an item, customer, subsidiary, term) does not exist or is not allowed on this record.",
      "Check the internal id in your mapping table. Is the item active and available for this subsidiary?",
      "Confirm the customer exists in NetSuite before its orders sync"),
    r("netsuite", "bad-value", r"INVALID_FLD_VALUE|invalid field value",
      "A value is not valid for the field: a picklist value, a format, a length.",
      "Compare the value with the allowed list or format in NetSuite", "Add it to the value map"),
    r("netsuite", "required-field", r"please enter value\(s\) for|required field|missing required|REQUIRED_FIELD",
      "NetSuite needs a field the sync did not supply (often subsidiary, terms, entity or an item).",
      "Add a default for the field or map it from Salesforce", "Set it as required in Salesforce so it is never empty"),
    r("netsuite", "closed-period", r"posting period|period .* closed|closed period",
      "The transaction date falls in a closed accounting period.",
      "Use a date in an open period, or ask Finance to reopen it. Do not retry unchanged"),
    r("netsuite", "permissions", r"INSUFFICIENT_PERMISSION|you do not have permission|permission violation",
      "The integration role cannot do this on this record type.",
      "Check the role's permissions for the record type and its sublists", "Do not use an administrator role"),
    r("netsuite", "stale-record", r"RCRD_HAS_BEEN_CHANGED|record has been changed|record was changed",
      "The record changed between read and write. A concurrent edit.",
      "Retry. A retry reads the current source values again", "If it repeats, look for another integration or a user editing it"),
    r("netsuite", "auth", r"INVALID_LOGIN_ATTEMPT|invalid login|token.*(invalid|expired)|unauthorized|401",
      "Authentication failed.",
      "Check the token-based authentication settings and the integration record", "Reconnect through the secure sign-in link. Never paste tokens in a chat"),
    r("netsuite", "currency-subsidiary", r"currency .* (not|isn't)|subsidiary .* (not|invalid)|not .*valid for .*subsidiary",
      "A currency or subsidiary combination is not allowed.",
      "Check the customer's subsidiary and currencies and the transaction's subsidiary match"),
    # ---- Salesforce
    r("salesforce", "daily-api-limit", r"TotalRequests",
      "The org used its daily API request allocation. It is shared by every integration.",
      "Check API usage and what else calls the API", "Lower the sync frequency and the per-app rate limit"),
    r("salesforce", "concurrency", r"Concurrent(PerOrg)?(LongTxn)?\s*Limit",
      "Too many long-running requests at once.", "Lower concurrency and batch sizes", "Look for slow automation on the written objects"),
    r("salesforce", "request-limit-unspecified", r"REQUEST_LIMIT_EXCEEDED",
      "A request limit was reached. The message does not say which.", "Check both the 24-hour API usage and long-running concurrent requests"),
    r("salesforce", "record-locking", r"UNABLE_TO_LOCK_ROW|exclusive access",
      "Parallel writes hit the same record or the same parent.", "Reduce parallel writes to related records", "Retry with backoff"),
    r("salesforce", "automation-limit", r"Too many SOQL|Too many DML|Apex CPU|heap size",
      "Salesforce automation fired by the write ran out of its own limits. Not an API limit.", "Send smaller batches", "Ask your admin to bulkify the automation"),
    r("salesforce", "validation", r"FIELD_CUSTOM_VALIDATION_EXCEPTION|REQUIRED_FIELD_MISSING|DUPLICATES_DETECTED|INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST|STRING_TOO_LONG|INVALID_CROSS_REFERENCE_KEY",
      "A validation rule, required field, duplicate rule, picklist or reference rejected the value. Not a limit.",
      "Fix the data or the rule. Retrying will not help"),
    r("salesforce", "access", r"INSUFFICIENT_ACCESS|FIELD_INTEGRITY|no access to field|INVALID_SESSION_ID",
      "A permission, field-level security or session problem.", "Check the connected user's profile and field-level security", "Reauthorize if the session expired"),
    r("salesforce", "api-not-enabled", r"REST API is not enabled|API_DISABLED_FOR_ORG",
      "The edition or user cannot use the API.", "Check the edition includes the API and the user has API Enabled"),
    # ---- the bridge between them
    r("sync", "item-list", r"itemList|lineList|line items?.*(invalid|empty|parse)",
      "The transaction's line array is invalid or incomplete. Lines live inside the transaction.",
      "Send the COMPLETE array every time", "Check every line's item id, quantity and rate"),
]
UNKNOWN = Rule("unknown", "unknown", re.compile("."), "No known pattern matched.", ("Read the full message and the failing record", "Check the sync's issues for the same record"))


def triage(message: str) -> Rule:
    for rule in RULES:
        if rule.pattern.search(message):
            return rule
    return UNKNOWN


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("message", nargs="?")
    parser.add_argument("--file")
    args = parser.parse_args()
    lines = [args.message] if args.message else open(args.file, encoding="utf-8").read().splitlines() if args.file else sys.stdin.read().splitlines()
    lines = [l for l in lines if l.strip()]

    if len(lines) == 1:
        rule = triage(lines[0])
        print(f"[{rule.side}] {rule.family}: {rule.meaning}")
        for step in rule.next_steps:
            print(f"  - {step}")
        return
    counts: dict[tuple[str, str], int] = {}
    for line in lines:
        rule = triage(line)
        counts[(rule.side, rule.family)] = counts.get((rule.side, rule.family), 0) + 1
    for (side, family), n in sorted(counts.items(), key=lambda x: -x[1]):
        rule = next(x for x in RULES + [UNKNOWN] if (x.side, x.family) == (side, family))
        print(f"{n:4}  [{side}] {family}: {rule.meaning}")


if __name__ == "__main__":
    main()
