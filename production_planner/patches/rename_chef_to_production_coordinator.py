"""Rename the restaurant-era Chef role, role profile and workspace for the vendor flow.

Runs before fixtures sync, so the fixtures then update the renamed records in
place. rename_doc carries every link with it: users' roles (Has Role), role
profiles, workflow transitions, Custom DocPerms and users' default workspace.
"""

import frappe

RENAMES = (
	("Role", "Chef", "Production Coordinator"),
	("Role Profile", "Chef", "Production Coordinator"),
	("Workspace", "Chef's Panel", "Production Tracking"),
)


def execute():
	log = frappe.logger("production_planner")
	for doctype, old, new in RENAMES:
		if not frappe.db.exists(doctype, old):
			log.info("[patch] %s %r not found, nothing to rename", doctype, old)
			continue
		if frappe.db.exists(doctype, new):
			log.warning("[patch] %s %r already exists, leaving %r in place", doctype, new, old)
			continue

		frappe.rename_doc(doctype, old, new, force=True, show_alert=False)
		log.info("[patch] renamed %s %r -> %r", doctype, old, new)

	# Role Profile keeps its own title field; Role keeps role_name. Fixtures fix the rest.
	if frappe.db.exists("Role", "Production Coordinator"):
		frappe.db.set_value("Role", "Production Coordinator", "role_name", "Production Coordinator")
	if frappe.db.exists("Role Profile", "Production Coordinator"):
		frappe.db.set_value(
			"Role Profile", "Production Coordinator", "role_profile", "Production Coordinator"
		)
