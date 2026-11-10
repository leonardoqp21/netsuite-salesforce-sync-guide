"""Check a field ownership matrix for a NetSuite and Salesforce sync before you build it.

Most sync conflicts are design problems: two teams both believe they own a field. Write down who
owns each field, which way it flows and what you decided about fields both sides may edit.

    python scripts/ownership_check.py ownership.example.json

It checks the matrix is consistent. It does not know how a particular sync resolves two edits made
close together. Test that in a sandbox and read the product documentation.
Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import json
import sys

OWNERS = {"netsuite", "salesforce", "both"}
DIRECTIONS = {"two_way", "netsuite_to_salesforce", "salesforce_to_netsuite"}
EXPECTED = {"netsuite": "netsuite_to_salesforce", "salesforce": "salesforce_to_netsuite", "both": "two_way"}
OWNER_FIELDS = {"salesRep", "OwnerId"}


def check(matrix: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    fields = matrix.get("fields", [])
    seen: set[tuple] = set()
    keys: dict[str, int] = {}
    objects: set[str] = set()

    for f in fields:
        label = f"{f.get('object', '?')}.{f.get('netsuite', '?')} / {f.get('salesforce', '?')}"
        objects.add(f.get("object", "?"))
        ident = (f.get("object"), f.get("netsuite"), f.get("salesforce"))
        if ident in seen:
            errors.append(f"{label}: listed twice")
        seen.add(ident)
        owner, direction = f.get("owner"), f.get("direction")
        if owner not in OWNERS:
            errors.append(f"{label}: owner must be one of {sorted(OWNERS)}")
            continue
        if direction not in DIRECTIONS:
            errors.append(f"{label}: direction must be one of {sorted(DIRECTIONS)}")
            continue
        if direction != EXPECTED[owner]:
            errors.append(f"{label}: owner '{owner}' should flow {EXPECTED[owner]}, not {direction}")
        if not str(f.get("reason", "")).strip():
            errors.append(f"{label}: write down why this system owns it")
        if owner == "both" and not str(f.get("conflict_plan", "")).strip():
            errors.append(f"{label}: both systems can edit it. Write the conflict plan you tested")
        if f.get("read_only") and owner == "both":
            errors.append(f"{label}: a read-only or computed field cannot be edited on both sides")
        if f.get("match_key"):
            keys[f["object"]] = keys.get(f["object"], 0) + 1
        if (f.get("netsuite") in OWNER_FIELDS or f.get("salesforce") in OWNER_FIELDS) and not f.get("owner_mapping"):
            errors.append(f"{label}: owner ids differ in each system. Add an owner_mapping table")
        if f.get("picklist") and not f.get("value_map"):
            errors.append(f"{label}: picklist values differ between systems. Add a value_map")
        if f.get("netsuite") in {"itemList", "lineList"} and direction == "two_way":
            errors.append(f"{label}: lines live inside the transaction. Do not make them two-way unless you own the rebuild of the complete array")

    for obj in sorted(objects):
        n = keys.get(obj, 0)
        if n == 0:
            errors.append(f"{obj}: no match key. Pick the field that says two records are the same")
        elif n > 1:
            warnings.append(f"{obj}: {n} match keys. Prefer one stable key")
    both = [f for f in fields if f.get("owner") == "both"]
    if fields and len(both) > len(fields) / 2:
        warnings.append("more than half of the fields are edited on both sides. That is where conflicts come from")
    return errors, warnings


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python ownership_check.py matrix.json")
    with open(sys.argv[1], encoding="utf-8") as fh:
        errors, warnings = check(json.load(fh))
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    if errors:
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
