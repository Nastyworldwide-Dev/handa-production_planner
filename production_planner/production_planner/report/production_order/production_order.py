# Copyright (c) 2025, Invento Software Limited and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _, copy_doc
from frappe.utils import flt
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{"label": "Action", "fieldname": "action", "fieldtype": "Data", "width": 200},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 220},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 220},
		{"label": "Order Qty", "fieldname": "order_qty", "fieldtype": "Float", "width": 100},
		{"label": "Produced Qty", "fieldname": "produced_qty", "fieldtype": "Float", "width": 120},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link",
		 "options": "Work Order", "width": 200}
	]


def get_data(filters=None):
	conditions = get_conditions(filters)

	query = """
			SELECT wo.name            AS work_order,
				   wo.production_item AS item_code,
				   wo.item_name       AS item_name,
				   wo.qty             AS order_qty,
				   wo.produced_qty    AS produced_qty,
				   wo.status          AS status,
				   wo.name            AS order_number,
				   wo.production_item AS production_item
			FROM `tabWork Order` wo
			WHERE wo.docstatus != 2 \
			"""

	if conditions:
		query += f" AND {conditions}"

	query += " ORDER BY wo.creation DESC"

	work_order_data = frappe.db.sql(query, filters, as_dict=1)

	for row in work_order_data:
		custom_status = "Not Started"

		docstatus = frappe.db.get_value("Work Order", row.work_order, "docstatus")

		if docstatus == 1:
			custom_status = "Preparing"

			se = frappe.db.sql("""
							   SELECT name, inspection_required
							   FROM `tabStock Entry`
							   WHERE work_order = %s
								 AND purpose = 'Manufacture'
							   ORDER BY creation DESC LIMIT 1
							   """, row.work_order, as_dict=1)

			if se:
				se_name = se[0].name
				inspection_required = se[0].inspection_required

				if inspection_required:
					finished_item = frappe.db.sql("""
												  SELECT quality_inspection, docstatus
												  FROM `tabStock Entry Detail`
												  WHERE parent = %s
													AND item_code = %s LIMIT 1
												  """, (se_name, row.item_code), as_dict=1)

					if finished_item and finished_item[0].quality_inspection:
						qc_name = finished_item[0].quality_inspection
						qc_docstatus = frappe.db.get_value("Quality Inspection", qc_name,
														   "docstatus")
						qc_status = frappe.db.get_value("Quality Inspection", qc_name, "status")

						if qc_status == "Accepted" and qc_docstatus == 1:
							custom_status = "Completed"
						elif qc_status == "Rejected" and qc_docstatus == 1:
							custom_status = "QC Rejected"
						else:
							custom_status = "Prepared"
					else:
						custom_status = "Prepared"
				else:
					custom_status = "Prepared"

		row["status"] = custom_status
		row["action"] = get_action_button(row["status"])

	return work_order_data


def get_conditions(filters):
	conditions = []

	if filters and filters.get("status"):
		conditions.append("wo.status = %(status)s")

	if filters and filters.get("work_order"):
		conditions.append("wo.name = %(work_order)s")

	if filters and filters.get("item_code"):
		conditions.append("wo.production_item = %(item_code)s")

	if filters and filters.get("from_date"):
		conditions.append("DATE(wo.creation) >= %(from_date)s")

	if filters and filters.get("to_date"):
		conditions.append("DATE(wo.creation) <= %(to_date)s")

	if filters and filters.get("company"):
		conditions.append("wo.company = %(company)s")

	return " AND ".join(conditions) if conditions else ""


def get_action_button(status):
	"""Determine what action button to show based on work order status"""
	action_mapping = {
		"Not Started": "Start",
		"Preparing": "Prepared",
		"Prepared": "Accept / Reject",
		"QC Rejected": "Reprepare",
		"Stopped": "Resume",
		"Closed": "View"
	}

	return action_mapping.get(status, "")


# Alternative safer approach using parameterized queries
def get_data_safe(filters=None):
	"""Alternative implementation with safer parameter handling"""

	query = """
			SELECT wo.name            as work_order, \
				   wo.production_item as item_code, \
				   wo.item_name       as item_name, \
				   wo.qty             as order_qty, \
				   wo.produced_qty    as produced_qty, \
				   wo.status          as status, \
				   wo.name            as order_number, \
				   wo.production_item as production_item
			FROM `tabWork Order` wo
			WHERE wo.docstatus = 1 \
			"""

	# Build conditions and parameters safely
	conditions = []
	query_params = {}

	if filters:
		if filters.get("status"):
			conditions.append("wo.status = %(status)s")
			query_params["status"] = filters["status"]

		if filters.get("work_order"):
			conditions.append("wo.name = %(work_order)s")
			query_params["work_order"] = filters["work_order"]

		if filters.get("item_code"):
			conditions.append("wo.production_item = %(item_code)s")
			query_params["item_code"] = filters["item_code"]

		if filters.get("from_date"):
			conditions.append("DATE(wo.creation) >= %(from_date)s")
			query_params["from_date"] = filters["from_date"]

		if filters.get("to_date"):
			conditions.append("DATE(wo.creation) <= %(to_date)s")
			query_params["to_date"] = filters["to_date"]

		if filters.get("company"):
			conditions.append("wo.company = %(company)s")
			query_params["company"] = filters["company"]

	if conditions:
		query += " AND " + " AND ".join(conditions)

	query += " ORDER BY wo.creation DESC"

	# Use query_params instead of filters directly
	work_order_data = frappe.db.sql(query, query_params, as_dict=1)

	# Add action buttons based on status
	for row in work_order_data:
		row['action'] = get_action_button(row['status'])

	return work_order_data


@frappe.whitelist()
def handle_action(action, order_no):
	if action == "Start":
		response = start_order(order_no)
	elif action == "Prepared":
		response = prepare_order(order_no)

	return response


def start_order(order_no):
	wo_doc = frappe.get_doc("Work Order", order_no)
	wo_doc.submit()

	if not wo_doc.skip_transfer:
		se_doc = frappe.get_doc(make_stock_entry(
			work_order_id=wo_doc.name,
			purpose="Material Transfer for Manufacture",
			qty=wo_doc.qty
		))

		se_doc = copy_doc(se_doc)
		se_doc.inspection_required = False
		se_doc.insert(ignore_permissions=True)
		se_doc.submit()

	return {
		"message": "Order Started",
		"data": {
			'order_no': wo_doc.name,
			'skip_transfer': wo_doc.skip_transfer,
			'qty': wo_doc.qty,
		}
	}


def prepare_order(order_no):
	wo_doc = frappe.get_doc("Work Order", order_no)
	se_doc = frappe.get_doc(make_stock_entry(
		work_order_id=wo_doc.name,
		purpose="Manufacture",
		qty=wo_doc.qty
	))
	se_doc.insert(ignore_permissions=True)

	return {
		"message": "Food Prepared Ready For QC",
		"data": {
			'order_no': wo_doc.name,
			'qty': wo_doc.qty,
		}
	}


@frappe.whitelist()
def create_quality_inspection(order_no, data):
	if isinstance(data, str):
		data = json.loads(data)

	stock_entries = frappe.get_all(
		"Stock Entry",
		filters={"work_order": order_no},
		fields=["name"]
	)

	if not stock_entries:
		frappe.throw(f"No Stock Entry found for Work Order {order_no}")

	se_doc = frappe.get_doc("Stock Entry", stock_entries[0].name)
	finished_items = [d for d in se_doc.items if d.is_finished_item]

	if not finished_items:
		frappe.throw(f"No finished item found in Stock Entry {se_doc.name}")

	if len(finished_items) > 1:
		frappe.throw(f"Multiple finished items found in Stock Entry {se_doc.name}")

	finished_item = finished_items[0]

	if flt(data.get("sample_size")) > flt(finished_item.get("qty")):
		frappe.throw(
			_(
				"{item_name}'s Sample Size ({sample_size}) cannot be greater than the Accepted Quantity ({accepted_quantity})"
			).format(
				item_name=finished_item.get("item_name"),
				sample_size=data.get("sample_size"),
				accepted_quantity=finished_item.get("qty"),
			)
		)

	quality_inspection = frappe.get_doc(
		{
			"doctype": "Quality Inspection",
			"inspection_type": "Incoming",
			"report_date": data.get("report_date"),
			"status": data.get("status"),
			"inspected_by": data.get("inspected_by"),
			"reference_type": se_doc.doctype,
			"reference_name": se_doc.name,
			"item_code": data.get("item_code"),
			"description": finished_item.get("description"),
			"sample_size": flt(data.get("sample_size")),
			"item_serial_no": finished_item.get("serial_no").split("\n")[0] if finished_item.get(
				"serial_no") else None,
			"batch_no": finished_item.get("batch_no"),
			"child_row_reference": finished_item.get("name"),
			"remarks": data.get("remarks"),
		}
	)
	quality_inspection.insert(ignore_permissions=True)
	quality_inspection.submit()
	if data.get("status") == "Accepted":
		se_doc = frappe.get_doc("Stock Entry", se_doc.name)
		se_doc.submit()

	return {
		"message": f"Quality Inspection {data.get('status')}.",
	}
