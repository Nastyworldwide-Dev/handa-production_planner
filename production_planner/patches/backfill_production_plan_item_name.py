import frappe
from frappe.modules.utils import sync_customizations


def execute():
	"""Fill item_name on existing Production Plan rows so their Item Code cell shows the name.

	fetch_from only runs when a row is saved, and submitted plans are never saved again.
	Custom fields are synced after post_model_sync patches, so add the column first.
	"""
	if not frappe.db.has_column("Production Plan Item", "item_name"):
		sync_customizations("production_planner")

	frappe.db.sql(
		"""
		UPDATE `tabProduction Plan Item` ppi
		INNER JOIN `tabItem` item ON item.name = ppi.item_code
		SET ppi.item_name = item.item_name
		WHERE IFNULL(ppi.item_name, '') = ''
		"""
	)
	frappe.logger("production_planner").info("[patch] backfilled item_name on Production Plan Item rows")
