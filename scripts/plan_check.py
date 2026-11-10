"""Check the plan of table pairs for a NetSuite and Salesforce sync BEFORE you build it.

A sync is a set of table pairs. They have dependencies (an order needs its customer and its items
to exist first), and each has a direction. This checks the plan is consistent.

    python scripts/plan_check.py samples/plan.example.json

Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import json
import sys

DIRECTIONS = {"two_way", "salesforce_to_netsuite", "netsuite_to_salesforce"}
# Records that only NetSuite can create or change. The CRM should only read them.
ERP_OWNED = {"invoice", "customer_payment", "item", "credit_memo", "item_fulfillment"}


def check(plan: dict) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, warnings, load_order)."""
    errors: list[str] = []
    warnings: list[str] = []
    pairs = {p["name"]: p for p in plan.get("pairs", [])}

    for name, p in pairs.items():
        if p.get("direction") not in DIRECTIONS:
            errors.append(f"{name}: direction must be one of {sorted(DIRECTIONS)}")
        for dep in p.get("depends_on", []):
            if dep not in pairs:
                errors.append(f"{name}: depends on {dep}, which is not in the plan")
        if p.get("netsuite") in ERP_OWNED and p.get("direction") not in {"netsuite_to_salesforce"}:
            errors.append(f"{name}: {p['netsuite']} is created in NetSuite. Sync it from NetSuite to Salesforce only")
        if p.get("netsuite") == "sales_order" and p.get("direction") == "two_way" and not p.get("lines_strategy"):
            errors.append(f"{name}: a two-way sales order needs a lines_strategy. Lines live inside the transaction")
        if p.get("netsuite") == "sales_order" and p.get("lines_strategy") not in {None, "workflow", "database_view"}:
            errors.append(f"{name}: lines_strategy must be workflow or database_view")
        if p.get("direction") == "two_way" and not p.get("ownership_reviewed"):
            warnings.append(f"{name}: two-way. Write the field ownership matrix and mark ownership_reviewed")

    # order: dependencies first
    order: list[str] = []
    seen: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str):
        if name in seen or name not in pairs:
            return
        if name in visiting:
            errors.append(f"circular dependency at {name}")
            return
        visiting.add(name)
        for dep in pairs[name].get("depends_on", []):
            visit(dep)
        visiting.discard(name)
        seen.add(name)
        order.append(name)

    for name in pairs:
        visit(name)

    for name, p in pairs.items():
        for dep in p.get("depends_on", []):
            if dep in order and order.index(dep) > order.index(name):
                errors.append(f"{name} would load before {dep}")
    if "sales_order" in {p.get("netsuite") for p in pairs.values()}:
        names = {p["netsuite"]: n for n, p in pairs.items()}
        for needed in ("customer", "item"):
            if needed not in names:
                warnings.append(f"sales orders need {needed}s to exist in both systems, but there is no {needed} pair in the plan")
    return errors, warnings, order


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python plan_check.py plan.json")
    with open(sys.argv[1], encoding="utf-8") as fh:
        errors, warnings, order = check(json.load(fh))
    print("Load order: " + " -> ".join(order))
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    if errors:
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
