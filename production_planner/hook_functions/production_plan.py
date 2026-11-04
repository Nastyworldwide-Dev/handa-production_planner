import frappe
from frappe import _
from frappe.utils import flt

from production_planner.production_planner.doctype.production_branch_warehouse.production_branch_warehouse import (
	get_branch_warehouses,
)
from production_planner.vendor_flow import (
	apply_availability,
	material_requirements,
	resolve_source_warehouse,
)
from production_planner.warehouse_rules import (
	branch_warehouse_message,
	branch_warehouse_offenders,
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


def validate_branch_warehouses(doc):
	"""Keep every warehouse on the plan inside its branch's group warehouse."""
	if not doc.get("custom_branch"):
		return

	branch, company, parent_warehouse = frappe.db.get_value(
		"Production Branch Warehouse", doc.custom_branch, ["branch", "company", "parent_warehouse"]
	)
	if company != doc.company:
		frappe.throw(
			_("Branch {0} belongs to {1}, not {2}.").format(branch, company, doc.company),
			title=_("Invalid Branch"),
		)

	offenders = branch_warehouse_offenders(
		warehouse_candidates(doc), get_branch_warehouses(parent_warehouse)
	)
	if offenders:
		frappe.logger("production_planner").warning(
			"[production_plan] %s blocked, outside branch %s: %s", doc.name, branch, offenders
		)
		frappe.throw(
			branch_warehouse_message(offenders, branch, parent_warehouse), title=_("Invalid Warehouse")
		)


def get_bom_lines(bom_nos):
	"""BOM quantity and single-level components for each BOM, in BOM order.

	Single level on purpose: a copack BOM lists the bulk liquid as one line;
	exploding it would wrongly ask the co-packer for the macerated oils.
	"""
	bom_nos = list({bom for bom in bom_nos if bom})
	if not bom_nos:
		return {}, {}

	bom_qty = dict(
		frappe.get_all("BOM", filters={"name": ("in", bom_nos)}, fields=["name", "quantity"], as_list=True)
	)
	lines = {}
	for line in frappe.get_all(
		"BOM Item",
		filters={"parent": ("in", bom_nos), "parenttype": "BOM"},
		fields=["parent", "item_code", "item_name", "stock_uom", "stock_qty", "source_warehouse"],
		order_by="parent, idx",
	):
		lines.setdefault(line.parent, []).append(line)
	return bom_qty, lines


def get_available_qty(pairs):
	"""Actual qty per (item_code, warehouse) from Bin; missing pairs are absent."""
	pairs = {(item, wh) for item, wh in pairs if item and wh}
	if not pairs:
		return {}

	bins = frappe.get_all(
		"Bin",
		filters={
			"item_code": ("in", list({item for item, _wh in pairs})),
			"warehouse": ("in", list({wh for _item, wh in pairs})),
		},
		fields=["item_code", "warehouse", "actual_qty"],
	)
	return {(b.item_code, b.warehouse): flt(b.actual_qty) for b in bins if (b.item_code, b.warehouse) in pairs}


def fill_materials(doc):
	"""List every material the vendor needs on the plan itself, with stock and shortage."""
	bom_qty, bom_lines = get_bom_lines(row.get("bom_no") for row in doc.get("po_items") or [])

	lines = []
	for row in doc.get("po_items") or []:
		per = flt(bom_qty.get(row.get("bom_no"))) or 1
		for line in bom_lines.get(row.get("bom_no"), []):
			lines.append(
				{
					"item_code": line.item_code,
					"item_name": line.item_name,
					"uom": line.stock_uom,
					"qty_per_unit": flt(line.stock_qty) / per,
					"planned_qty": flt(row.get("planned_qty")),
					"warehouse": resolve_source_warehouse(
						line.source_warehouse, row.get("custom_source_warehouse"), doc.get("custom_source_warehouse")
					),
				}
			)

	requirements = material_requirements(lines)
	available = get_available_qty((r["item_code"], r["warehouse"]) for r in requirements)
	materials = apply_availability(requirements, available)

	doc.set("custom_materials", [])
	for material in materials:
		doc.append("custom_materials", material)

	short = [m["item_code"] for m in materials if m["shortage_qty"] > 0]
	frappe.logger("production_planner").info(
		"[production_plan] %s materials listed: %s lines, %s short %s",
		doc.name, len(materials), len(short), short,
	)


def validate(doc, method=None):
	validate_warehouses(doc)
	validate_branch_warehouses(doc)
	fill_materials(doc)


def on_submit(doc, method):
	validate_warehouses(doc)

	try:
		doc.make_work_order()

		work_orders = frappe.get_all(
			"Work Order",
			filters={"production_plan": doc.name, "docstatus": 0},
			fields=["name"]
		)

		bom_nos = list({row.get("bom_no") for row in doc.po_items if row.get("bom_no")})
		_bom_qty, bom_lines = get_bom_lines(bom_nos)
		lead_times = dict(
			frappe.get_all(
				"BOM",
				filters={"name": ("in", bom_nos or [""])},
				fields=["name", "custom_lead_time_days"],
				as_list=True,
			)
		)

		for wo in work_orders:
			wo_doc = frappe.get_doc("Work Order", wo.name)
			wo_doc.fg_warehouse = doc.custom_finished_goods_warehouse
			wo_doc.source_warehouse = doc.custom_source_warehouse
			wo_doc.wip_warehouse = doc.custom_wip_warehouse
			if doc.get("custom_wastage_warehouse"):
				wo_doc.scrap_warehouse = doc.custom_wastage_warehouse
			if doc.custom__skip_material_transfer_to_wip_warehouse:
				wo_doc.skip_transfer = 1
			wo_doc.custom_process_type = doc.get("custom_process_type")
			wo_doc.custom_vendor = doc.get("custom_branch")
			wo_doc.custom_lead_time_days = lead_times.get(wo_doc.bom_no) or 0
			wo_doc.save()

			# A BOM line's own source warehouse (e.g. bulk liquid vs packaging store) wins.
			line_sources = {line.item_code: line.source_warehouse for line in bom_lines.get(wo_doc.bom_no, [])}
			for item in wo_doc.required_items:
				item.source_warehouse = resolve_source_warehouse(
					line_sources.get(item.item_code), None, doc.custom_source_warehouse
				)
				item.save()

			frappe.logger("production_planner").info(
				"[production_plan] %s -> %s: %s at %s, lead time %s days",
				doc.name, wo_doc.name, wo_doc.custom_process_type, wo_doc.custom_vendor,
				wo_doc.custom_lead_time_days,
			)

			frappe.db.commit()

	except Exception as e:
		frappe.throw(_("Failed to create or submit Work Orders: {0}").format(e))
