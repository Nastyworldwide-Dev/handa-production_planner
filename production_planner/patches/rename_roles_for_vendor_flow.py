"""Standardise roles for the vendor flow under one "Production ..." prefix.

Chef becomes Production Coordinator (with its role profile and workspace),
QC becomes Production QC, and Production becomes Production Admin. The Chef
role profile and Chef's Panel workspace were renamed with the Chef role; every
other role profile and workspace keeps its name, only the roles inside change.

Runs in [pre_model_sync]: DocType sync creates any missing role named in a
DocType's permissions (make_module_and_roles), which would make the new name
exist already and strand users on the old role. Fixtures sync later and update
the renamed records in place. rename_doc carries every link with it: users' roles (Has Role), role
profiles, workflow transitions, Custom DocPerms and users' default workspace.
"""

import frappe

RENAMES = (
	("Role", "Chef", "Production Coordinator"),
	("Role", "QC", "Production QC"),
	("Role", "Production", "Production Admin"),
	("Role Profile", "Chef", "Production Coordinator"),
	("Workspace", "Chef's Panel", "Production Tracking"),
)


def execute():
	log = frappe.logger("production_planner")
	for doctype, old, new in RENAMES:
		if not frappe.db.exists(doctype, old):
			log.info("[patch] %s %r not found, nothing to rename", doctype, old)
			continue
		merge = bool(frappe.db.exists(doctype, new))
		if merge and doctype != "Role":
			log.warning("[patch] %s %r already exists, leaving %r in place", doctype, new, old)
			continue

		# These roles belong to this app. If the new one already exists (created by
		# hand or an earlier build), merge so users and permissions move across
		# instead of silently staying on the old role.
		frappe.rename_doc(doctype, old, new, force=True, merge=merge, show_alert=False)
		log.info("[patch] %s %s %r -> %r", "merged" if merge else "renamed", doctype, old, new)

	# Role and Role Profile keep their own title fields; rename_doc only changes the name.
	for role in ("Production Coordinator", "Production QC", "Production Admin"):
		if frappe.db.exists("Role", role):
			frappe.db.set_value("Role", role, "role_name", role)
	if frappe.db.exists("Role Profile", "Production Coordinator"):
		frappe.db.set_value(
			"Role Profile", "Production Coordinator", "role_profile", "Production Coordinator"
		)
