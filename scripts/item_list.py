"""Turn Salesforce order lines into the NetSuite `itemList`, and back.

In the NetSuite connector a transaction is ONE record. Its lines are a JSON array in a single
field (`itemList` for most transactions). Lines cannot sync as a separate table, and to add, change
or remove a line you must write the COMPLETE updated array. Salesforce stores the same lines as
separate rows (order items). This module is the bridge:

    build_item_list(order_items, item_map)     Salesforce rows  ->  itemList array
    explode_item_list(item_list, item_map_rev) itemList array   ->  rows, for reporting
    change_line(item_list, line, **changes)    returns the COMPLETE new array
    diff_item_lists(old, new)                  what changed, by line

Money is Decimal. The `item_map` (Salesforce product code -> NetSuite item internalId) is YOURS.
Standard library only. Python 3.9 or newer.
"""
from __future__ import annotations

import copy
from decimal import Decimal, InvalidOperation


class MappingError(ValueError):
    """A line cannot be built. The message says which line and why, so a person can fix the data."""


def _dec(value, what: str, line: int) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise MappingError(f"line {line}: {what} is not a number: {value!r}") from None


def build_item_list(order_items: list[dict], item_map: dict[str, str]) -> list[dict]:
    """Build the complete itemList for one order.

    order_items: [{"product_code": "SKU-1", "quantity": 2, "unit_price": "10.00"}, ...] in line order.
    item_map:    {"SKU-1": "38704"}  Salesforce product code -> NetSuite item internalId.
    """
    if not order_items:
        raise MappingError("an order needs at least one line")
    out: list[dict] = []
    for number, row in enumerate(order_items, 1):
        code = row.get("product_code")
        if not code:
            raise MappingError(f"line {number}: no product code")
        if code not in item_map:
            raise MappingError(f"line {number}: product {code} has no NetSuite item in the mapping")
        qty = _dec(row.get("quantity"), "quantity", number)
        price = _dec(row.get("unit_price"), "unit price", number)
        if qty <= 0:
            raise MappingError(f"line {number}: quantity must be above zero")
        if price < 0:
            raise MappingError(f"line {number}: unit price cannot be negative")
        out.append({"item": {"internalId": item_map[code]}, "quantity": _plain(qty), "rate": _plain(price), "line": number})
    return out


def _plain(value: Decimal):
    """10.0 stays 10.0, 2 stays 2. JSON numbers, no scientific notation."""
    return int(value) if value == value.to_integral_value() else float(value)


def explode_item_list(item_list: list[dict], reverse_map: dict[str, str]) -> list[dict]:
    """One row per line, for reporting. Changes meant for NetSuite must go back into the array, not these rows."""
    rows = []
    for line in item_list:
        item_id = str(line["item"]["internalId"])
        rows.append({
            "line": line["line"], "item_id": item_id, "product_code": reverse_map.get(item_id),
            "quantity": line["quantity"], "rate": line["rate"],
            "amount": float(Decimal(str(line["quantity"])) * Decimal(str(line["rate"]))),
        })
    return rows


def change_line(item_list: list[dict], line: int, **changes) -> list[dict]:
    """Return the COMPLETE array with one line changed. Never send only the changed line."""
    new = copy.deepcopy(item_list)
    target = next((l for l in new if l["line"] == line), None)
    if target is None:
        raise MappingError(f"no line {line}")
    for key, value in changes.items():
        if key not in {"quantity", "rate"}:
            raise MappingError(f"only quantity and rate can change, not {key}")
        target[key] = value
    return new


def remove_line(item_list: list[dict], line: int) -> list[dict]:
    """Return the COMPLETE array without a line. Remaining lines are renumbered from 1."""
    kept = [copy.deepcopy(l) for l in item_list if l["line"] != line]
    if len(kept) == len(item_list):
        raise MappingError(f"no line {line}")
    if not kept:
        raise MappingError("removing the last line would leave an empty order")
    for number, l in enumerate(kept, 1):
        l["line"] = number
    return kept


def diff_item_lists(old: list[dict], new: list[dict]) -> dict:
    old_by, new_by = {l["line"]: l for l in old}, {l["line"]: l for l in new}
    return {
        "added": sorted(set(new_by) - set(old_by)),
        "removed": sorted(set(old_by) - set(new_by)),
        "changed": sorted(n for n in set(old_by) & set(new_by) if old_by[n] != new_by[n]),
    }


def order_total(item_list: list[dict]) -> Decimal:
    return sum((Decimal(str(l["quantity"])) * Decimal(str(l["rate"])) for l in item_list), Decimal("0"))
