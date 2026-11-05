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
		self.assertEqual(
			self.fields["custom_branch_warehouse"]["fetch_from"], "custom_branch.parent_warehouse"
		)
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
		shortcut = next(s for s in panel["shortcuts"] if s["link_to"] == "Production Branch Warehouse")
		shortcut_blocks = [
			b["data"]["shortcut_name"] for b in json.loads(panel["content"]) if b["type"] == "shortcut"
		]
		# Content blocks reference shortcuts by label, which is "Vendor Warehouse Setup" now.
		self.assertIn(shortcut["label"], shortcut_blocks)

	def test_every_content_shortcut_has_a_shortcut_row(self):
		"""Renamed labels must be renamed in the page content too, or the tile vanishes."""
		for name, ws in self.workspaces.items():
			labels = {s["label"] for s in ws["shortcuts"]}
			for block in json.loads(ws["content"]):
				if block["type"] == "shortcut":
					self.assertIn(block["data"]["shortcut_name"], labels, name)

	def test_vendor_tracker_on_coordinator_and_production_panels(self):
		for name in ("Production Tracking", "Production Panel"):
			self.assertIn("Vendor Tracker", [s["link_to"] for s in self.workspaces[name]["shortcuts"]], name)

	def test_admin_panel_production_card_links_branch_warehouse(self):
		links = self.workspaces["Admin Panel"]["links"]
		card = next(
			i
			for i, link in enumerate(links)
			if link["type"] == "Card Break" and link["label"] == "Production"
		)
		card_links = links[card + 1 : card + 1 + links[card]["link_count"]]
		self.assertTrue(all(link["type"] == "Link" for link in card_links))
		self.assertIn("Production Branch Warehouse", [link["link_to"] for link in card_links])


if __name__ == "__main__":
	unittest.main()


ROLE_KEYS = frozenset({"role", "allowed", "allow_edit", "completed_by_role", "role_name"})
OLD_ROLES = {"Chef": "Production Coordinator", "QC": "Production QC", "Production": "Production Admin"}


def role_values(obj, doctype=None):
	"""Every role name a JSON export refers to, including Role records' own names."""
	if isinstance(obj, list):
		for item in obj:
			yield from role_values(item, doctype)
		return
	if not isinstance(obj, dict):
		return
	doctype = obj.get("doctype") or doctype
	for key, value in obj.items():
		if isinstance(value, (dict, list)):
			yield from role_values(value, doctype)
		elif key in ROLE_KEYS or (key == "name" and doctype == "Role"):
			yield value


class TestVendorRename(unittest.TestCase):
	"""Roles share one prefix: Production Admin / Coordinator / QC. Nothing may point back."""

	def test_no_json_uses_old_role_names(self):
		offenders = set()
		for path in APP_ROOT.rglob("*.json"):
			with open(path) as f:
				for value in role_values(json.load(f)):
					if value in OLD_ROLES:
						offenders.add((str(path.relative_to(APP_ROOT)), value))
		self.assertEqual(sorted(offenders), [])

	def test_role_fixture_filters_use_new_names(self):
		hooks = (APP_ROOT / "hooks.py").read_text()
		for old, new in OLD_ROLES.items():
			self.assertIn(f'"{new}"', hooks)
			self.assertNotIn(f'"in", ["{old}"', hooks)

	def test_js_role_checks_use_new_names(self):
		for path in APP_ROOT.rglob("*.js"):
			text = path.read_text()
			for old in OLD_ROLES:
				self.assertNotIn(f'has_role("{old}")', text, str(path))

	def test_patch_renames_every_old_role(self):
		patch = (APP_ROOT / "patches" / "rename_roles_for_vendor_flow.py").read_text()
		for old, new in OLD_ROLES.items():
			self.assertIn(f'("Role", "{old}", "{new}")', patch)

	def test_no_json_references_chef_role(self):
		offenders = []
		for path in APP_ROOT.rglob("*.json"):
			text = path.read_text()
			if '"Chef"' in text or "Chef's Panel" in text or "chef's-panel" in text:
				offenders.append(str(path.relative_to(APP_ROOT)))
		self.assertEqual(offenders, [])

	def test_rename_patch_registered(self):
		patches = (APP_ROOT / "patches.txt").read_text()
		self.assertIn("production_planner.patches.rename_roles_for_vendor_flow", patches)
		self.assertNotIn("rename_chef_to_production_coordinator", patches)


class TestWhitelistedEndpoints(unittest.TestCase):
	"""Report buttons call whitelisted methods that move stock with ignore_permissions.

	Any logged-in user can call a whitelisted method directly, so each one that
	acts on a Work Order must check the caller's permission on it first.
	"""

	REPORT = APP_ROOT / "production_planner" / "report" / "production_order" / "production_order.py"
	GUARDED = frozenset({"handle_action", "create_quality_inspection"})

	def test_stock_moving_endpoints_check_permission(self):
		import ast

		tree = ast.parse(self.REPORT.read_text())
		found = {}
		for node in tree.body:
			if isinstance(node, ast.FunctionDef) and node.name in self.GUARDED:
				calls = {
					ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)
				}
				found[node.name] = "frappe.has_permission" in calls
		self.assertEqual(found, {name: True for name in self.GUARDED})

	def test_vendor_tracker_respects_user_permissions(self):
		source = (
			APP_ROOT / "production_planner" / "report" / "vendor_tracker" / "vendor_tracker.py"
		).read_text()
		# The listed jobs must go through get_list (user permissions); get_all only for history.
		self.assertIn('frappe.get_list(\n\t\t"Work Order"', source)

	def test_patch_runs_before_model_sync(self):
		"""DocType sync auto-creates any role named in its permissions (make_module_and_roles).

		If the rename ran after model sync, "Production Admin" would already exist,
		the patch would skip, and existing users would be stranded on "Production".
		"""
		patches = (APP_ROOT / "patches.txt").read_text()
		pre, _sep, post = patches.partition("[post_model_sync]")
		self.assertIn("production_planner.patches.rename_roles_for_vendor_flow", pre)
		self.assertNotIn("production_planner.patches.rename_roles_for_vendor_flow", post)
