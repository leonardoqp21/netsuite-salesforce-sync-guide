import json
import pathlib
import sqlite3
import sys
import unittest
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import item_list as il  # noqa: E402
from error_triage import triage  # noqa: E402
from ownership_check import check as check_ownership  # noqa: E402
from plan_check import check as check_plan  # noqa: E402

ITEM_MAP = {"SKU-A": "38704", "SKU-B": "38705"}
ROWS = [{"product_code": "SKU-A", "quantity": 2, "unit_price": "10.00"}, {"product_code": "SKU-B", "quantity": 1, "unit_price": "25.00"}]


class ItemListTests(unittest.TestCase):
    def test_builds_the_documented_shape(self):
        self.assertEqual(il.build_item_list(ROWS, ITEM_MAP), [
            {"item": {"internalId": "38704"}, "quantity": 2, "rate": 10, "line": 1},
            {"item": {"internalId": "38705"}, "quantity": 1, "rate": 25, "line": 2}])

    def test_a_product_without_a_mapping_is_an_error_that_names_the_line(self):
        with self.assertRaisesRegex(il.MappingError, "line 2: product SKU-X has no NetSuite item"):
            il.build_item_list([ROWS[0], {"product_code": "SKU-X", "quantity": 1, "unit_price": "1"}], ITEM_MAP)

    def test_bad_numbers_and_empty_orders(self):
        for bad, text in [({"product_code": "SKU-A", "quantity": "x", "unit_price": "1"}, "quantity is not a number"),
                          ({"product_code": "SKU-A", "quantity": 0, "unit_price": "1"}, "above zero"),
                          ({"product_code": "SKU-A", "quantity": 1, "unit_price": "-1"}, "negative"),
                          ({"quantity": 1, "unit_price": "1"}, "no product code")]:
            with self.subTest(text=text), self.assertRaisesRegex(il.MappingError, text):
                il.build_item_list([bad], ITEM_MAP)
        with self.assertRaises(il.MappingError):
            il.build_item_list([], ITEM_MAP)

    def test_decimals_are_exact(self):
        out = il.build_item_list([{"product_code": "SKU-A", "quantity": 3, "unit_price": "0.1"}], ITEM_MAP)
        self.assertEqual(il.order_total(out), Decimal("0.3"))

    def test_round_trip_for_reporting(self):
        built = il.build_item_list(ROWS, ITEM_MAP)
        rows = il.explode_item_list(built, {v: k for k, v in ITEM_MAP.items()})
        self.assertEqual([r["product_code"] for r in rows], ["SKU-A", "SKU-B"])
        self.assertEqual(rows[0]["amount"], 20.0)

    def test_changing_a_line_returns_the_complete_array(self):
        built = il.build_item_list(ROWS, ITEM_MAP)
        new = il.change_line(built, 2, quantity=3)
        self.assertEqual(len(new), 2)
        self.assertEqual(new[1]["quantity"], 3)
        self.assertEqual(built[1]["quantity"], 1)  # the original is untouched
        self.assertEqual(il.diff_item_lists(built, new), {"added": [], "removed": [], "changed": [2]})

    def test_only_quantity_and_rate_can_change(self):
        with self.assertRaises(il.MappingError):
            il.change_line(il.build_item_list(ROWS, ITEM_MAP), 1, item="x")

    def test_removing_a_line_renumbers_and_keeps_the_rest(self):
        new = il.remove_line(il.build_item_list(ROWS, ITEM_MAP), 1)
        self.assertEqual([l["line"] for l in new], [1])
        self.assertEqual(new[0]["item"]["internalId"], "38705")
        with self.assertRaises(il.MappingError):
            il.remove_line(new, 1)

    def test_diff(self):
        old = il.build_item_list(ROWS, ITEM_MAP)
        new = il.build_item_list(ROWS + [{"product_code": "SKU-A", "quantity": 1, "unit_price": "5"}], ITEM_MAP)
        self.assertEqual(il.diff_item_lists(old, new)["added"], [3])


class SqlViewTests(unittest.TestCase):
    def setUp(self):
        db = sqlite3.connect(":memory:")
        db.executescript("""
            CREATE TABLE sf_account(id TEXT, netsuite_internal_id TEXT);
            CREATE TABLE sf_order(id TEXT, account_id TEXT, po_number TEXT, effective_date TEXT);
            CREATE TABLE order_item(order_id TEXT, product_code TEXT, quantity REAL, unit_price REAL, line_number INTEGER);
            CREATE TABLE item_map(product_code TEXT, netsuite_item_id TEXT);
            INSERT INTO sf_account VALUES ('A1','1001'), ('A2', NULL);
            INSERT INTO sf_order VALUES ('O1','A1','PO-9','2026-11-01'), ('O2','A2','PO-8','2026-11-02');
            INSERT INTO order_item VALUES ('O1','SKU-A',2,10.0,1), ('O1','SKU-B',1,25.0,2), ('O2','SKU-A',1,10.0,1);
            INSERT INTO item_map VALUES ('SKU-A','38704'), ('SKU-B','38705');
        """)
        db.executescript((ROOT / "sql" / "sales_order_view.sqlite.sql").read_text())
        self.rows = db.execute("SELECT * FROM sales_order_for_netsuite").fetchall()

    def test_one_row_per_order_with_a_json_array_of_lines(self):
        self.assertEqual(len(self.rows), 1)
        lines = json.loads(self.rows[0][4])
        self.assertEqual([l["item"]["internalId"] for l in lines], ["38704", "38705"])
        self.assertEqual(lines[0]["quantity"], 2)

    def test_orders_for_customers_not_in_the_erp_yet_are_held_back(self):
        self.assertNotIn("O2", [r[0] for r in self.rows])

    def test_the_view_matches_the_python_builder(self):
        lines = json.loads(self.rows[0][4])
        built = il.build_item_list(ROWS, ITEM_MAP)
        self.assertEqual([(l["item"]["internalId"], float(l["quantity"]), float(l["rate"]), l["line"]) for l in lines],
                         [(l["item"]["internalId"], float(l["quantity"]), float(l["rate"]), l["line"]) for l in built])

    def test_postgres_version_exists_and_is_labeled_untested(self):
        text = (ROOT / "sql" / "sales_order_view.postgres.sql").read_text()
        self.assertIn("NOT run by this repo's tests", text)
        self.assertIn("jsonb_agg", text)


class PlanTests(unittest.TestCase):
    PLAN = json.loads((ROOT / "samples" / "plan.example.json").read_text())

    def test_example_plan_is_valid_and_ordered(self):
        errors, warnings, order = check_plan(self.PLAN)
        self.assertEqual((errors, warnings), ([], []))
        self.assertLess(order.index("customers"), order.index("orders"))
        self.assertLess(order.index("items"), order.index("orders"))
        self.assertLess(order.index("orders"), order.index("invoices"))

    def test_invoices_must_flow_from_the_erp(self):
        plan = json.loads(json.dumps(self.PLAN))
        next(p for p in plan["pairs"] if p["name"] == "invoices")["direction"] = "two_way"
        self.assertTrue(any("created in NetSuite" in e for e in check_plan(plan)[0]))

    def test_unknown_dependency_and_cycle(self):
        plan = {"pairs": [{"name": "a", "netsuite": "customer", "direction": "two_way", "depends_on": ["b"], "ownership_reviewed": True},
                          {"name": "b", "netsuite": "contact", "direction": "two_way", "depends_on": ["a"], "ownership_reviewed": True}]}
        self.assertTrue(any("circular" in e for e in check_plan(plan)[0]))
        plan = {"pairs": [{"name": "a", "netsuite": "customer", "direction": "two_way", "depends_on": ["zzz"]}]}
        self.assertTrue(any("not in the plan" in e for e in check_plan(plan)[0]))

    def test_two_way_orders_need_a_lines_strategy_and_orders_need_customers(self):
        plan = {"pairs": [{"name": "orders", "netsuite": "sales_order", "direction": "two_way", "ownership_reviewed": True}]}
        errors, warnings, _ = check_plan(plan)
        self.assertTrue(any("lines_strategy" in e for e in errors))
        self.assertTrue(any("customer" in w for w in warnings))

    def test_a_two_way_pair_without_reviewed_ownership_is_warned(self):
        plan = {"pairs": [{"name": "customers", "netsuite": "customer", "direction": "two_way"}]}
        self.assertTrue(any("ownership" in w for w in check_plan(plan)[1]))


class OwnershipTests(unittest.TestCase):
    M = json.loads((ROOT / "ownership.example.json").read_text())

    def test_example_is_valid(self):
        self.assertEqual(check_ownership(self.M)[0], [])

    def test_owner_must_match_direction(self):
        m = json.loads(json.dumps(self.M))
        m["fields"][2]["direction"] = "two_way"
        self.assertTrue(any("should flow" in e for e in check_ownership(m)[0]))

    def test_both_needs_a_conflict_plan_and_picklists_need_maps(self):
        m = json.loads(json.dumps(self.M))
        for f in m["fields"]:
            f.pop("conflict_plan", None)
            f.pop("value_map", None)
            f.pop("owner_mapping", None)
        errors = check_ownership(m)[0]
        for text in ["conflict plan", "value_map", "owner_mapping"]:
            self.assertTrue(any(text in e for e in errors), text)

    def test_every_object_needs_one_match_key(self):
        m = json.loads(json.dumps(self.M))
        for f in m["fields"]:
            f.pop("match_key", None)
        self.assertEqual(len([e for e in check_ownership(m)[0] if "no match key" in e]), 2)

    def test_lines_are_not_two_way(self):
        m = json.loads(json.dumps(self.M))
        line = next(f for f in m["fields"] if f["netsuite"] == "itemList")
        line.update(owner="both", direction="two_way", conflict_plan="x")
        self.assertTrue(any("lines live inside" in e for e in check_ownership(m)[0]))


class TriageTests(unittest.TestCase):
    CASES = {
        "SSS_REQUEST_LIMIT_EXCEEDED: Request limit exceeded": ("netsuite", "concurrency"),
        "INVALID_KEY_OR_REF: Invalid item reference key 99999": ("netsuite", "bad-reference"),
        "INVALID_FLD_VALUE: You have entered an Invalid Field Value Net 99": ("netsuite", "bad-value"),
        "Please enter value(s) for: Terms": ("netsuite", "required-field"),
        "You cannot create a transaction in a closed posting period": ("netsuite", "closed-period"),
        "INSUFFICIENT_PERMISSION: You do not have permission": ("netsuite", "permissions"),
        "RCRD_HAS_BEEN_CHANGED: Record has been changed": ("netsuite", "stale-record"),
        "INVALID_LOGIN_ATTEMPT: Invalid login attempt": ("netsuite", "auth"),
        "REQUEST_LIMIT_EXCEEDED: TotalRequests Limit exceeded.": ("salesforce", "daily-api-limit"),
        "REQUEST_LIMIT_EXCEEDED: ConcurrentPerOrgLongTxn Limit exceeded.": ("salesforce", "concurrency"),
        "UNABLE_TO_LOCK_ROW: unable to obtain exclusive access": ("salesforce", "record-locking"),
        "System.LimitException: Too many SOQL queries: 101": ("salesforce", "automation-limit"),
        "FIELD_CUSTOM_VALIDATION_EXCEPTION: nope": ("salesforce", "validation"),
        "INSUFFICIENT_ACCESS_OR_READONLY": ("salesforce", "access"),
        "The REST API is not enabled for this Organization": ("salesforce", "api-not-enabled"),
        "itemList is invalid": ("sync", "item-list"),
        "who knows": ("unknown", "unknown"),
    }

    def test_known_messages(self):
        for message, want in self.CASES.items():
            with self.subTest(message=message):
                r = triage(message)
                self.assertEqual((r.side, r.family), want)
                self.assertTrue(r.next_steps)

    def test_sample_file(self):
        lines = [l for l in (ROOT / "samples" / "errors.txt").read_text().splitlines() if l.strip()]
        families = {(triage(l).side, triage(l).family) for l in lines}
        self.assertLessEqual({("netsuite", "bad-reference"), ("salesforce", "validation"), ("unknown", "unknown")}, families)


class HygieneTests(unittest.TestCase):
    def test_no_em_dashes(self):
        for path in ROOT.rglob("*.md"):
            self.assertNotIn(chr(0x2014), path.read_text(encoding="utf-8"), str(path))


if __name__ == "__main__":
    unittest.main()
