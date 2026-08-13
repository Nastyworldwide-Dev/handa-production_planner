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


if __name__ == "__main__":
	unittest.main()
