import frappe
from frappe import _

from production_planner.warehouse_rules import (
	group_warehouse_message,
	group_warehouse_offenders,
	warehouse_candidates,
)


def get_group_warehouses(names):
	"""Names among `names` that are group nodes in the Warehouse tree."""
	names = {name for name in names if name}
	if not names:
		return set()

	groups = frappe.get_all(
		"Warehouse",
		filters={"name": ("in", list(names)), "is_group": 1},
		pluck="name",
	)
	frappe.logger("production_planner").debug(
		"[production_plan] checked %s warehouses, %s are group nodes", len(names), len(groups)
	)
	return set(groups)


def validate_warehouses(doc):
	"""Reject group warehouses before they reach Work Orders and Stock Entries.

	ERPNext only raises "Group node warehouse is not allowed to select for
	transactions" when the Stock Ledger Entry is written on submit — for this
	app that is the QC Accept click, several steps after the wrong warehouse
	was picked. Fail here instead, naming the field.
	"""
	candidates = warehouse_candidates(doc)
	groups = get_group_warehouses(warehouse for _label, warehouse in candidates)
	offenders = group_warehouse_offenders(candidates, groups)

	if offenders:
		frappe.logger("production_planner").warning(
			"[production_plan] %s blocked, group warehouses: %s", doc.name, offenders
		)
		frappe.throw(group_warehouse_message(offenders), title=_("Invalid Warehouse"))


def validate(doc, method=None):
	validate_warehouses(doc)


def on_submit(doc, method):
	validate_warehouses(doc)

	try:
		doc.make_work_order()

		work_orders = frappe.get_all(
			"Work Order",
			filters={"production_plan": doc.name, "docstatus": 0},
			fields=["name"]
		)

		for wo in work_orders:
			wo_doc = frappe.get_doc("Work Order", wo.name)
			wo_doc.fg_warehouse = doc.custom_finished_goods_warehouse
			wo_doc.source_warehouse = doc.custom_source_warehouse
			wo_doc.wip_warehouse = doc.custom_wip_warehouse
			if doc.custom__skip_material_transfer_to_wip_warehouse:
				wo_doc.skip_transfer = 1
			wo_doc.save()

			for item in wo_doc.required_items:
				item.source_warehouse = doc.custom_source_warehouse
				item.save()

			frappe.db.commit()

	except Exception as e:
		frappe.throw(_("Failed to create or submit Work Orders: {0}").format(e))
