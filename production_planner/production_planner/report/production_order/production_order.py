# Copyright (c) 2025, Invento Software Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _


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

	# Build the query safely
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
			WHERE wo.docstatus != 2 \
			"""

	# Add conditions if they exist
	if conditions:
		query += f" AND {conditions}"

	query += " ORDER BY wo.creation DESC"

	work_order_data = frappe.db.sql(query, filters, as_dict=1)

	# Add action buttons based on status
	for row in work_order_data:
		row['action'] = get_action_button(row['status'])

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
		"Draft": "Start",
		"Not Started": "Start",
		"In Process": "Prepared",
		"Completed": "Accept / Reject",
		"Submitted": "Finish",
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

	return response


def start_order(order_no):
	wo_doc = frappe.get_doc("Work Order", order_no)
	wo_doc.submit()
	return {
		"message": "Order Started",
		"data": {
			'order_no': wo_doc.name,
			'skip_transfer': wo_doc.skip_transfer,
			'qty': wo_doc.qty,
		}
	}
