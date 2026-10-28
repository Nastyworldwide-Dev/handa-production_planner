"""Guards against group (parent-node) warehouses reaching stock transactions.

A Warehouse with `is_group = 1` is a folder in the warehouse tree, not a
stockable location. ERPNext only rejects it when the Stock Ledger Entry is
written — i.e. at *submit* — with:

    Group node warehouse is not allowed to select for transactions

In this app the warehouses travel Production Plan -> Work Order -> Stock Entry
programmatically, so nothing stops a group node until the QC "Accept" button
submits the Manufacture Stock Entry, long after the mistake was made. These
tests pin the two defences: link filters on the pickers, and an early check.
"""

import json
import logging
import unittest
from pathlib import Path

from production_planner.warehouse_rules import (
	branch_profile_candidates,
	branch_warehouse_message,
	branch_warehouse_offenders,
	group_warehouse_message,
	group_warehouse_offenders,
	stock_entry_candidates,
	warehouse_candidates,
)

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_DIR = APP_ROOT / "production_planner" / "custom"


class TestWarehouseLinkFilters(unittest.TestCase):
	"""Every custom Warehouse picker must hide group nodes."""

	def warehouse_fields(self):
		for path in sorted(CUSTOM_DIR.glob("*.json")):
			with open(path) as f:
				data = json.load(f)
			for field in data.get("custom_fields") or []:
				if field.get("fieldtype") == "Link" and field.get("options") == "Warehouse":
					yield path.name, field

	def test_warehouse_fields_exist(self):
		self.assertTrue(list(self.warehouse_fields()), "no Warehouse custom fields found")

	def test_warehouse_fields_filter_out_group_nodes(self):
		offenders = []
		for filename, field in self.warehouse_fields():
			raw = field.get("link_filters")
			filters = json.loads(raw) if isinstance(raw, str) else (raw or [])
			has_guard = any(
				len(f) >= 4 and f[1] == "is_group" and f[2] == "=" and not f[3] for f in filters
			)
			if not has_guard:
				offenders.append(f"{filename}: {field.get('fieldname')} link_filters={raw!r}")

		self.assertEqual(
			offenders,
			[],
			'Warehouse custom fields must carry link_filters [["Warehouse","is_group","=",0]] '
			"so a group node can never be picked:\n  " + "\n  ".join(offenders),
		)


class TestGroupWarehouseOffenders(unittest.TestCase):
	"""The pure rule behind the server-side guard."""

	def test_returns_empty_when_all_leaf_warehouses(self):
		candidates = [("Source Warehouse", "Stores - AS"), ("WIP Warehouse", "Kitchen - AS")]
		self.assertEqual(group_warehouse_offenders(candidates, group_names=set()), [])

	def test_flags_group_warehouse_with_its_label(self):
		candidates = [
			("Source Warehouse", "All Warehouses - AS"),
			("WIP Warehouse", "Kitchen - AS"),
		]
		self.assertEqual(
			group_warehouse_offenders(candidates, group_names={"All Warehouses - AS"}),
			[("Source Warehouse", "All Warehouses - AS")],
		)

	def test_ignores_blank_warehouses(self):
		candidates = [("Source Warehouse", None), ("WIP Warehouse", "")]
		self.assertEqual(group_warehouse_offenders(candidates, group_names={"x"}), [])

	def test_deduplicates_repeated_label_warehouse_pairs(self):
		candidates = [("Row 1 Source Warehouse", "Grp - AS")] * 3
		self.assertEqual(
			group_warehouse_offenders(candidates, group_names={"Grp - AS"}),
			[("Row 1 Source Warehouse", "Grp - AS")],
		)

	def test_message_names_field_and_warehouse(self):
		message = group_warehouse_message([("WIP Warehouse", "All Warehouses - AS")])
		self.assertIn("WIP Warehouse", message)
		self.assertIn("All Warehouses - AS", message)

	def test_message_is_empty_without_offenders(self):
		self.assertEqual(group_warehouse_message([]), "")


class TestBranchWarehouseOffenders(unittest.TestCase):
	"""Warehouses on a branch's plan must sit under that branch's group warehouse."""

	def test_returns_empty_when_all_inside_branch(self):
		candidates = [("Source Warehouse", "Inventory CK Tampin - DHSB")]
		self.assertEqual(
			branch_warehouse_offenders(candidates, {"Inventory CK Tampin - DHSB"}),
			[],
		)

	def test_flags_warehouse_from_another_branch(self):
		candidates = [
			("Source Warehouse", "Inventory CK Tampin - DHSB"),
			("Finished Goods Warehouse", "Inventory CK Seremban - DHSB"),
		]
		self.assertEqual(
			branch_warehouse_offenders(candidates, {"Inventory CK Tampin - DHSB"}),
			[("Finished Goods Warehouse", "Inventory CK Seremban - DHSB")],
		)

	def test_ignores_blanks_and_deduplicates(self):
		candidates = [("Source Warehouse", None), ("Row 1 Source Warehouse", "X - DHSB")] + [
			("Row 2 Source Warehouse", "Y - DHSB")
		] * 2
		self.assertEqual(
			branch_warehouse_offenders(candidates, {"X - DHSB"}),
			[("Row 2 Source Warehouse", "Y - DHSB")],
		)

	def test_message_names_branch_parent_and_offender(self):
		message = branch_warehouse_message(
			[("Wastage Warehouse", "Wastage - CK Seremban - DHSB")], "CK Tampin", "CK Tampin - DHSB"
		)
		self.assertIn("CK Tampin - DHSB", message)
		self.assertIn("Wastage Warehouse", message)
		self.assertIn("Wastage - CK Seremban - DHSB", message)

	def test_message_is_empty_without_offenders(self):
		self.assertEqual(branch_warehouse_message([], "CK Tampin", "CK Tampin - DHSB"), "")

	def test_profile_candidates_cover_all_four_warehouses(self):
		profile = {
			"source_warehouse": "Src - DHSB",
			"wip_warehouse": "Wip - DHSB",
			"fg_warehouse": "Fg - DHSB",
			"wastage_warehouse": "Waste - DHSB",
		}
		self.assertEqual(
			branch_profile_candidates(profile),
			[
				("Source Warehouse", "Src - DHSB"),
				("Work-in-Progress Warehouse", "Wip - DHSB"),
				("Finished Goods Warehouse", "Fg - DHSB"),
				("Wastage Warehouse", "Waste - DHSB"),
			],
		)


class TestCandidateBuilders(unittest.TestCase):
	"""Where the guards look for warehouses."""

	def test_production_plan_candidates_cover_header_and_rows(self):
		doc = {
			"custom_source_warehouse": "Src - AS",
			"custom_wip_warehouse": "Wip - AS",
			"custom_finished_goods_warehouse": "Fg - AS",
			"custom_wastage_warehouse": "Waste - AS",
			"po_items": [
				{
					"idx": 1,
					"custom_source_warehouse": "Row Src - AS",
					"custom_wip_warehouse": "Row Wip - AS",
					"warehouse": "Row Fg - AS",
				}
			],
		}
		candidates = warehouse_candidates(doc)

		self.assertIn(("Source Warehouse", "Src - AS"), candidates)
		self.assertIn(("Work-in-Progress Warehouse", "Wip - AS"), candidates)
		self.assertIn(("Finished Goods Warehouse", "Fg - AS"), candidates)
		self.assertIn(("Wastage Warehouse", "Waste - AS"), candidates)
		self.assertIn(("Row 1 Source Warehouse", "Row Src - AS"), candidates)
		self.assertIn(("Row 1 Finished Goods Warehouse", "Row Fg - AS"), candidates)

	def test_production_plan_candidates_tolerate_missing_rows(self):
		self.assertTrue(warehouse_candidates({}))

	def test_stock_entry_candidates_cover_both_row_warehouses(self):
		doc = {
			"from_warehouse": "Wip - AS",
			"to_warehouse": "Fg - AS",
			"items": [
				{"idx": 1, "item_code": "RICE", "s_warehouse": "Wip - AS", "t_warehouse": None},
				{"idx": 2, "item_code": "MEAL", "s_warehouse": None, "t_warehouse": "Fg - AS"},
			],
		}
		candidates = stock_entry_candidates(doc)

		self.assertIn(("Default Source Warehouse", "Wip - AS"), candidates)
		self.assertIn(("Default Target Warehouse", "Fg - AS"), candidates)
		self.assertIn(("Row 1 (RICE) Source Warehouse", "Wip - AS"), candidates)
		self.assertIn(("Row 2 (MEAL) Target Warehouse", "Fg - AS"), candidates)


if __name__ == "__main__":
	unittest.main()
