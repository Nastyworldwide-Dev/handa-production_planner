# Copyright (c) 2025, Invento Software Limited and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	filters = filters or {}
	data = []

	conditions = ["se.stock_entry_type = 'Material Consumption for Manufacture'", "se.docstatus = 1"]

	if filters.get("from_date") and filters.get("to_date"):
		conditions.append("se.posting_date BETWEEN %(from_date)s AND %(to_date)s")
	elif filters.get("from_date"):
		conditions.append("se.posting_date >= %(from_date)s")
	elif filters.get("to_date"):
		conditions.append("se.posting_date <= %(to_date)s")

	if filters.get("company"):
		conditions.append("se.company = %(company)s")

	if filters.get("consumption_reason"):
		conditions.append("se.custom_consumption_reason = %(consumption_reason)s")

	condition_str = " AND ".join(conditions)

	stock_entries = frappe.db.sql(f"""
		SELECT
			se.name,
			se.posting_date,
			se.company,
			se.custom_consumption_reason,
			se.custom_reason_description
		FROM
			`tabStock Entry` se
		WHERE
			{condition_str}
		ORDER BY
			se.posting_date DESC
	""", filters, as_dict=True)

	for se in stock_entries:
		items = frappe.db.sql("""
			SELECT item_code, item_name, qty, basic_rate, amount
			FROM `tabStock Entry Detail`
			WHERE parent = %s
			ORDER BY idx ASC
		""", se.name, as_dict=True)

		if not items:
			continue

		first_item = items[0]
		data.append({
			"indent": 0,
			"is_group": 1,
			"posting_date": se.posting_date,
			"company": se.company,
			"stock_entry": se.name,
			"consumption_reason": se.custom_consumption_reason,
			"description": se.custom_reason_description,
			"item_code": first_item.item_code,
			"item_name": first_item.item_name,
			"qty": first_item.qty,
			"rate": first_item.basic_rate,
			"amount": first_item.amount
		})

		for item in items[1:]:
			data.append({
				"indent": 1,
				"is_group": 0,
				"posting_date": "",
				"company": "",
				"stock_entry": "",
				"consumption_reason": "",
				"description": "",
				"item_code": item.item_code,
				"item_name": item.item_name,
				"qty": item.qty,
				"rate": item.basic_rate,
				"amount": item.amount
			})

	summary = get_summary(data, filters)

	chart = get_chart_data(filters)

	return get_columns(), data, None, chart, summary


def get_columns():
	return [
		{"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 150},
		{"label": "Stock Entry", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 180},
		{"label": "Consumption Reason", "fieldname": "consumption_reason", "fieldtype": "Data", "width": 150},
		{"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 120},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 80},
		{"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 100},
		{"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
	]


def get_summary(data, filters):
	if not data:
		return []

	currency = None
	if filters.get("company"):
		currency = frappe.db.get_value("Company", filters["company"], "default_currency")
	if not currency:
		currency = frappe.defaults.get_global_default("currency")

	total_amount = sum(d.get("amount") or 0 for d in data)
	total_qty = sum(d.get("qty") or 0 for d in data)
	total_entries = len(set(d.get("stock_entry") for d in data if d.get("stock_entry")))

	return [
		{"label": "Total Stock Entries", "value": total_entries, "indicator": "Blue"},
		{"label": "Total Quantity", "value": total_qty, "indicator": "Green"},
		{"label": "Total Amount", "value": frappe.utils.fmt_money(total_amount or 0, currency=currency), "indicator": "Red"}
	]


def get_chart_data(filters):
	chart_data = frappe.db.sql(f"""
		SELECT
			COALESCE(se.custom_consumption_reason, 'Not Specified') AS reason,
			SUM(sed.qty) AS total_qty
		FROM
			`tabStock Entry` se
			JOIN `tabStock Entry Detail` sed ON sed.parent = se.name
		WHERE
			se.stock_entry_type = 'Material Consumption for Manufacture'
			AND se.docstatus = 1
			{ "AND se.company = %(company)s" if filters.get("company") else "" }
			{ "AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s" if filters.get("from_date") and filters.get("to_date") else "" }
		GROUP BY
			se.custom_consumption_reason
		ORDER BY
			total_amount DESC
	""", filters, as_dict=True)

	if not chart_data:
		return None

	return {
		"data": {
			"labels": [d.reason for d in chart_data],
			"datasets": [
				{
					"name": "Consumption QTY",
					"values": [d.total_qty for d in chart_data]
				}
			]
		},
		"type": "donut",
		"colors": ["#2490ef", "#46c35f", "#ffb822", "#f4516c", "#34bfa3", "#716aca"]
	}

