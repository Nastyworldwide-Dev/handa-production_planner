# Copyright (c) 2026, Invento Software Limited and contributors
# For license information, please see license.txt

"""Every job sent to a vendor, against its BOM lead time.

Answers "when will the liquid / finished goods be back?" and, from jobs that
have come back, "how long does this formula really take at this vendor?".
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from production_planner.vendor_flow import average_actual_days, days_left, timing_state

OPEN_STATES = ("Not Sent", "No Lead Time", "On Track", "Due Soon", "Overdue")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	frappe.logger("production_planner").info("[vendor_tracker] %s jobs for %s", len(data), dict(filters))
	return get_columns(), data, None, None, get_summary(data)


def get_columns():
	return [
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 150,
		},
		{"label": _("Process"), "fieldname": "process_type", "fieldtype": "Data", "width": 100},
		{
			"label": _("Vendor Site"),
			"fieldname": "vendor",
			"fieldtype": "Link",
			"options": "Production Branch Warehouse",
			"width": 170,
		},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 180},
		{"label": _("Qty"), "fieldname": "qty", "fieldtype": "Float", "width": 80},
		{"label": _("Sent On"), "fieldname": "sent_on", "fieldtype": "Date", "width": 100},
		{"label": _("Lead Time (Days)"), "fieldname": "lead_time_days", "fieldtype": "Int", "width": 90},
		{"label": _("Expected Ready"), "fieldname": "expected_ready_on", "fieldtype": "Date", "width": 115},
		{"label": _("Days Left"), "fieldname": "days_left", "fieldtype": "Int", "width": 80},
		{"label": _("Received On"), "fieldname": "received_on", "fieldtype": "Date", "width": 110},
		{"label": _("Actual Days"), "fieldname": "actual_days", "fieldtype": "Int", "width": 90},
		{
			"label": _("Avg Actual Days"),
			"fieldname": "avg_actual_days",
			"fieldtype": "Float",
			"width": 110,
			"precision": 1,
		},
		{"label": _("Timing"), "fieldname": "timing", "fieldtype": "Data", "width": 130},
		{"label": _("BOM"), "fieldname": "bom_no", "fieldtype": "Link", "options": "BOM", "width": 150},
	]


def get_data(filters):
	conditions = {"docstatus": ("!=", 2), "custom_process_type": ("is", "set")}
	for key, field in (
		("company", "company"),
		("process_type", "custom_process_type"),
		("vendor", "custom_vendor"),
		("item_code", "production_item"),
	):
		if filters.get(key):
			conditions[field] = filters.get(key)

	# get_list applies the user's permissions (e.g. restricted to one company).
	rows = frappe.get_list(
		"Work Order",
		filters=conditions,
		fields=[
			"name as work_order",
			"custom_process_type as process_type",
			"custom_vendor as vendor",
			"production_item as item_code",
			"item_name",
			"qty",
			"bom_no",
			"custom_sent_on as sent_on",
			"custom_lead_time_days as lead_time_days",
			"custom_expected_ready_on as expected_ready_on",
			"custom_received_on as received_on",
			"custom_actual_days as actual_days",
		],
		order_by="custom_expected_ready_on asc, creation desc",
	)

	# History across all jobs (not just the filtered ones) so the average is meaningful.
	history = frappe.get_all(
		"Work Order",
		filters={"docstatus": 1, "custom_actual_days": ("is", "set")},
		fields=["bom_no", "custom_vendor as vendor", "custom_actual_days as actual_days"],
	)
	averages = average_actual_days(history)

	today = getdate(nowdate())
	for row in rows:
		row.days_left = None if row.received_on else days_left(row.expected_ready_on, today)
		row.timing = timing_state(row.sent_on, row.expected_ready_on, row.received_on, today)
		row.avg_actual_days = averages.get((row.bom_no, row.vendor))

	if filters.get("open_only"):
		rows = [row for row in rows if row.timing in OPEN_STATES]
	if filters.get("timing"):
		rows = [row for row in rows if row.timing == filters.get("timing")]
	return rows


def get_summary(data):
	count = {}
	for row in data:
		count[row.timing] = count.get(row.timing, 0) + 1

	cards = [
		("Overdue", "Red"),
		("Due Soon", "Orange"),
		("On Track", "Blue"),
		("Received On Time", "Green"),
		("Received Late", "Orange"),
	]
	return [
		{"value": count.get(label, 0), "label": _(label), "indicator": color, "datatype": "Int"}
		for label, color in cards
	]
