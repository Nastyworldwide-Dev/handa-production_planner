"""Guards on the exported customization files in production_planner/custom/.

`bench export-customizations` writes *every* Custom Field and Property Setter
attached to a DocType, not just the ones this app owns. When the export is taken
from a site that has other apps installed, their fields ride along and break
`bench install-app` on any site lacking those apps:

    WrongOptionsDoctypeLinkError: Sales Invoice: Options must be a valid DocType
    for field Restaurant in row 68

These tests fail on that class of contamination without needing a live bench.
"""

import json
import logging
import unittest
from pathlib import Path

logger = logging.getLogger(__name__)

APP_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_DIR = APP_ROOT / "production_planner" / "custom"
DOCTYPE_DIR = APP_ROOT / "production_planner" / "doctype"

LINK_FIELDTYPES = {"Link", "Table", "Table MultiSelect"}

# DocTypes shipped by frappe/erpnext that this app is allowed to link to.
# Anything outside this set plus the app's own DocTypes means a foreign app's
# customization has been exported into this repo.
CORE_DOCTYPES = {
	"Account",
	"Item",
	"Item Group",
	"Sales Invoice",
	"Warehouse",
	"Work Order",
	"Workflow State",
}


def app_doctypes() -> set[str]:
	"""DocType names defined by this app, read from their JSON definitions."""
	names = set()
	for definition in DOCTYPE_DIR.glob("*/*.json"):
		with open(definition) as f:
			data = json.load(f)
		if data.get("doctype") == "DocType" and data.get("name"):
			names.add(data["name"])
	return names


def customization_files() -> list[Path]:
	return sorted(CUSTOM_DIR.glob("*.json"))


class TestCustomizations(unittest.TestCase):
	def setUp(self):
		self.allowed = CORE_DOCTYPES | app_doctypes()
		logger.debug("[customizations] allowed link targets: %s", sorted(self.allowed))

	def test_custom_dir_is_present(self):
		self.assertTrue(CUSTOM_DIR.is_dir(), f"missing customization dir: {CUSTOM_DIR}")
		self.assertTrue(customization_files(), "no customization files found")

	def test_link_fields_target_available_doctypes(self):
		"""Every Link/Table custom field must point at a DocType the install will have."""
		offenders = []
		for path in customization_files():
			with open(path) as f:
				data = json.load(f)
			for field in data.get("custom_fields") or []:
				if field.get("fieldtype") not in LINK_FIELDTYPES:
					continue
				options = field.get("options")
				if options not in self.allowed:
					offenders.append(f"{path.name}: {field.get('fieldname')} -> {options!r}")

		self.assertEqual(
			offenders,
			[],
			"Custom fields link to DocTypes this app does not guarantee. Either the "
			"providing app belongs in hooks.required_apps, or the field was picked up "
			"from a foreign site during export and must be removed:\n  " + "\n  ".join(offenders),
		)

	def test_no_orphan_insert_after_targets(self):
		"""insert_after must name a field the same file defines, or a non-custom field.

		A custom field inserted after another app's custom field silently lands in
		the wrong place (or at the end) on a site without that app.
		"""
		offenders = []
		for path in customization_files():
			with open(path) as f:
				data = json.load(f)
			fields = data.get("custom_fields") or []
			own = {field.get("fieldname") for field in fields}
			for field in fields:
				target = field.get("insert_after")
				# custom_* / foreign prefixes only exist if another app created them
				if target and target.startswith("custom_") and target not in own:
					offenders.append(f"{path.name}: {field.get('fieldname')} after {target!r}")

		self.assertEqual(
			offenders,
			[],
			"custom fields anchored to fields no app in this repo creates:\n  " + "\n  ".join(offenders),
		)


class TestProductionPlanBranchFields(unittest.TestCase):
	"""Production Plan carries the branch that picks its warehouses."""

	def setUp(self):
		with open(CUSTOM_DIR / "production_plan.json") as f:
			self.data = json.load(f)
		self.fields = {field["fieldname"]: field for field in self.data["custom_fields"]}

	def test_branch_and_wastage_fields_exist(self):
		self.assertEqual(self.fields["custom_branch"]["options"], "Production Branch Warehouse")
		self.assertEqual(self.fields["custom_branch_warehouse"]["fetch_from"], "custom_branch.parent_warehouse")
		self.assertEqual(self.fields["custom_wastage_warehouse"]["options"], "Warehouse")

	def test_field_order_places_branch_after_company(self):
		setter = next(p for p in self.data["property_setters"] if p["property"] == "field_order")
		order = json.loads(setter["value"])
		self.assertEqual(order[order.index("company") + 1], "custom_branch")
		self.assertIn("custom_wastage_warehouse", order)


class TestProductionBranchWarehouseDocType(unittest.TestCase):
	"""One warehouse profile per company + branch."""

	def setUp(self):
		path = DOCTYPE_DIR / "production_branch_warehouse" / "production_branch_warehouse.json"
		with open(path) as f:
			self.data = json.load(f)
		self.fields = {field["fieldname"]: field for field in self.data["fields"]}

	def test_shows_branch_name_in_links(self):
		self.assertEqual(self.data["title_field"], "branch")
		self.assertTrue(self.data.get("show_title_field_in_link"))

	def test_name_is_unique_per_company_and_branch(self):
		self.assertIn("{branch}", self.data["autoname"])
		self.assertIn("{company}", self.data["autoname"])

	def test_keys_and_parent_are_required(self):
		for fieldname in ("company", "branch", "parent_warehouse"):
			self.assertTrue(self.fields[fieldname].get("reqd"), fieldname)

	def test_holds_all_four_warehouses(self):
		for fieldname in ("source_warehouse", "wip_warehouse", "fg_warehouse", "wastage_warehouse"):
			self.assertEqual(self.fields[fieldname]["options"], "Warehouse", fieldname)


class TestProductionPlanItemName(unittest.TestCase):
	"""ERPNext shows "CODE: Item Name" in a row's Item Code cell only when the row has item_name."""

	def setUp(self):
		with open(CUSTOM_DIR / "production_plan_item.json") as f:
			self.data = json.load(f)
		self.fields = {field["fieldname"]: field for field in self.data["custom_fields"]}

	def test_item_name_is_fetched_from_item_code(self):
		field = self.fields["item_name"]
		self.assertEqual(field["fetch_from"], "item_code.item_name")
		self.assertTrue(field["read_only"])

	def test_item_name_follows_item_code_in_field_order(self):
		setter = next(p for p in self.data["property_setters"] if p["property"] == "field_order")
		order = json.loads(setter["value"])
		self.assertEqual(order[order.index("item_code") + 1], "item_name")

	def test_existing_rows_are_backfilled(self):
		patches = (APP_ROOT / "patches.txt").read_text()
		self.assertIn("production_planner.patches.backfill_production_plan_item_name", patches)
		self.assertTrue((APP_ROOT / "patches" / "backfill_production_plan_item_name.py").is_file())


class TestWorkspaceLinks(unittest.TestCase):
	"""Branch warehouse profiles must be reachable from the panels that use them."""

	def setUp(self):
		with open(APP_ROOT / "fixtures" / "workspace.json") as f:
			self.workspaces = {w["name"]: w for w in json.load(f)}

	def test_production_panel_has_branch_warehouse_shortcut(self):
		panel = self.workspaces["Production Panel"]
		self.assertIn("Production Branch Warehouse", [s["link_to"] for s in panel["shortcuts"]])
		shortcut_blocks = [
			b["data"]["shortcut_name"] for b in json.loads(panel["content"]) if b["type"] == "shortcut"
		]
		self.assertIn("Production Branch Warehouse", shortcut_blocks)

	def test_admin_panel_production_card_links_branch_warehouse(self):
		links = self.workspaces["Admin Panel"]["links"]
		card = next(i for i, link in enumerate(links) if link["type"] == "Card Break" and link["label"] == "Production")
		card_links = links[card + 1 : card + 1 + links[card]["link_count"]]
		self.assertTrue(all(link["type"] == "Link" for link in card_links))
		self.assertIn("Production Branch Warehouse", [link["link_to"] for link in card_links])


if __name__ == "__main__":
	unittest.main()
