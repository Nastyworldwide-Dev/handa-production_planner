# Copyright (c) 2025, Invento Software Limited and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _, copy_doc
from frappe.utils import flt, nowdate
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry


def execute(filters=None):
	if not filters:
		filters = {}

	columns, data = get_columns(), get_data(filters)
	charts = get_charts(filters, data)
	summary = get_report_summary(filters, data)
	return columns, data, None, charts, summary



def get_columns():
	return [
		{"label": "Action", "fieldname": "action", "fieldtype": "Data", "width": 160},
		{"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 180},
		{"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 210},
		{"label": "Order Qty", "fieldname": "order_qty", "fieldtype": "Float", "width": 100},
		{"label": "Produced Qty", "fieldname": "produced_qty", "fieldtype": "Float", "width": 120},
		{"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
		{"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link",
		 "options": "Work Order", "width": 150},
		{"label": "View Actions", "fieldname": "view_recipe", "fieldtype": "HTML", "width": 160},
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
				   wo.production_item AS production_item,
				   wo.bom_no AS bom_no
			FROM `tabWork Order` wo
			WHERE wo.docstatus != 2 \
			"""

	if conditions:
		query += f" AND {conditions}"

	query += " ORDER BY wo.creation DESC"

	work_order_data = frappe.db.sql(query, filters, as_dict=1)

	for row in work_order_data:
		custom_status = "Pending"

		docstatus = frappe.db.get_value("Work Order", row.work_order, "docstatus")

		if docstatus == 1:
			custom_status = "In Progress"

			se = frappe.db.sql("""
							   SELECT name, inspection_required, docstatus
							   FROM `tabStock Entry`
							   WHERE work_order = %s
								 AND purpose = 'Manufacture'
							   ORDER BY creation DESC LIMIT 1
							   """, row.work_order, as_dict=1)

			if se:
				se_name = se[0].name
				docstatus = se[0].docstatus
				inspection_required = se[0].inspection_required
				if docstatus == 1:
					custom_status = "Completed"
				elif docstatus == 0 and inspection_required:
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
							custom_status = "Ready For QC"
					else:
						custom_status = "Ready For QC"
				else:
					custom_status = "Ready For QC"

		row["status"] = custom_status
		row["action"] = get_action_button(row["status"])
		bom_no = row.get("bom_no")
		work_order = row.get("work_order")

		if bom_no and work_order:
			bom_url = f"/printview?doctype=BOM&name={bom_no}&trigger_print=0"
			work_order_url = f"/printview?doctype=Work Order&name={work_order}&trigger_print=0"
			row["view_recipe"] = f'''
		        <div style="display: flex; gap: 5px;">
		            <a class="btn btn-xs btn-success" href="{bom_url}" target="_blank">Recipe</a>
		            <a class="btn btn-xs btn-warning" href="{work_order_url}" target="_blank">Materials</a>
		        </div>
		    '''
		else:
			row["view_recipe"] = ""

	if filters and filters.get("status"):
		filtered_data = [row for row in work_order_data if row["status"] in filters.get("status")]
		return filtered_data

	return work_order_data


def get_conditions(filters):
	conditions = []

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
		"Pending": "Start",
		"In Progress": "Prepared",
		"Ready For QC": "Accept / Reject",
		"QC Rejected": "Reprepared"
	}

	return action_mapping.get(status, "")


def get_report_summary(filters, data):
	"""Generate number cards for the report"""
	if not data:
		return []

	# Calculate summary statistics
	total_orders = len(data)
	total_order_qty = sum(flt(row.get('order_qty', 0)) for row in data)
	total_produced_qty = sum(flt(row.get('produced_qty', 0)) for row in data)

	# Count orders by status
	status_count = {}
	for row in data:
		status = row.get('status', 'Unknown')
		status_count[status] = status_count.get(status, 0) + 1

	# Calculate completion rate
	completion_rate = 0
	if total_order_qty > 0:
		completion_rate = (total_produced_qty / total_order_qty) * 100

	report_summary = []

	for status, count in status_count.items():
		indicator_color = get_status_indicator(status)
		report_summary.append({
			"value": count,
			"indicator": indicator_color,
			"label": _(status),
			"datatype": "Int",
		})

	# Add totals after status counts
	report_summary.extend([
		{
			"value": total_orders,
			"indicator": "Blue",
			"label": _("Total Work Orders"),
			"datatype": "Int",
		},
		{
			"value": total_order_qty,
			"indicator": "Green" if completion_rate > 50 else "Orange",
			"label": _("Total Order Qty"),
			"datatype": "Float",
		},
		{
			"value": f"{completion_rate:.1f}%",
			"indicator": "Green" if completion_rate > 75 else "Orange" if completion_rate > 50 else "Red",
			"label": _("Completion Rate"),
			"datatype": "Percent",
		}
	])

	return report_summary


def get_status_indicator(status):
	"""Get indicator color based on status"""
	color_map = {
		"Completed": "Green",
		"In Progress": "Blue",
		"Ready For QC": "Orange",
		"QC Rejected": "Red",
		"Pending": "Gray"
	}
	return color_map.get(status, "Gray")


def get_charts(filters, data):
	"""Generate charts for the report"""
	# if not data:
	# 	return []
	#
	# # Production Efficiency (Bar Chart)
	# if len(data) > 0:
	# 	sorted_data = sorted(data, key=lambda x: flt(x.get('order_qty', 0)), reverse=True)
	#
	# 	if sorted_data:
	# 		efficiency_chart = {
	# 			"title": _("Top Work Orders by Order Quantity"),
	# 			"data": {
	# 				"labels": [row.get('work_order', '') for row in sorted_data],
	# 				"datasets": [
	# 					{
	# 						"name": _("Order Qty"),
	# 						"values": [flt(row.get('order_qty', 0)) for row in sorted_data]
	# 					},
	# 					{
	# 						"name": _("Produced Qty"),
	# 						"values": [flt(row.get('produced_qty', 0)) for row in sorted_data]
	# 					}
	# 				]
	# 			},
	# 			"type": "bar",
	# 			"height": 300,
	# 		}
	# 		return efficiency_chart
	return None


def get_monthly_trend_data(filters):
	"""Get monthly work order creation trend data"""
	conditions = get_conditions(filters)

	query = """
			SELECT DATE_FORMAT(creation, '%%Y-%%m') as month,
               COUNT(*) as count
			FROM `tabWork Order`
			WHERE docstatus != 2 \
			"""

	if conditions:
		query += f" AND {conditions}"

	query += """
        GROUP BY DATE_FORMAT(creation, '%Y-%m')
        ORDER BY month
    """

	result = frappe.db.sql(query, filters, as_dict=True)

	monthly_data = {}
	for row in result:
		monthly_data[row.month] = row.count

	return monthly_data


@frappe.whitelist()
def handle_action(action, order_no):
	if action == "Start":
		response = start_order(order_no)
	elif action == "Prepared":
		response = prepare_order(order_no)
	elif action == "Reprepared":
		response = reprepare_oder(order_no)
	return response


def start_order(order_no):
	wo_doc = frappe.get_doc("Work Order", order_no)
	wo_doc.workflow_state = "In Progress"
	wo_doc.save(ignore_permissions=True)
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
	wo_doc.workflow_state = "Ready For QC"
	wo_doc.save(ignore_permissions=True)
	wo_doc.submit()
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
		wo_doc = frappe.get_doc("Work Order", order_no)
		wo_doc.workflow_state = "Completed"
	else:
		wo_doc = frappe.get_doc("Work Order", order_no)
		wo_doc.workflow_state = "QC Rejected"
	wo_doc.save(ignore_permissions=True)
	wo_doc.submit()

	return {
		"message": f"Quality Inspection {data.get('status')}.",
	}


def reprepare_oder(order_no):
	wo_doc = frappe.get_doc("Work Order", order_no)
	wo_doc.workflow_state = "Ready For QC"
	wo_doc.save(ignore_permissions=True)
	wo_doc.submit()

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
	finished_item.quality_inspection = ""
	se_doc.save(ignore_permissions=True)

	return {
		'message': "Order Reprepared",
	}


@frappe.whitelist()
def make_inter_company_transfer(items, target_company, source_company, price_list):
	if isinstance(items, str):
		items = json.loads(items)

	if not source_company:
		frappe.throw(_("Source Company is required"))

	# Check for already transferred items
	already_transferred = []
	for item in items:
		wo_name = item.get("work_order")
		if not wo_name:
			continue
		
		# Check if a non-cancelled Delivery Note Item already exists for this Work Order
		# We check for custom_work_order field
		existing_dn = frappe.db.get_value("Delivery Note Item", 
			{"custom_work_order": wo_name, "docstatus": ["<", 2]}, 
			"parent")
		
		if existing_dn:
			already_transferred.append({
				"work_order": wo_name,
				"delivery_note": existing_dn
			})

	if already_transferred:
		msg = _("The following items have already been transferred:")
		msg += "<ul style='margin-top: 10px;'>"
		for entry in already_transferred:
			dn_link = f'<a href="/app/delivery-note/{entry["delivery_note"]}" target="_blank">{entry["delivery_note"]}</a>'
			msg += f"<li>{_('Work Order')}: <b>{entry['work_order']}</b> ({_('Delivery Note')}: {dn_link})</li>"
		msg += "</ul>"
		return msg

	# Find Internal Customer
	internal_customer = frappe.db.get_value("Customer", {
		"represents_company": target_company,
		"is_internal_customer": 1
	}, "name")

	if not internal_customer:
		frappe.throw(_("No Internal Customer found for Company {0} in Company {1}. Please configure an Internal Customer.").format(target_company, source_company))

	# Create Delivery Note
	dn = frappe.new_doc("Delivery Note")
	dn.company = source_company
	dn.customer = internal_customer
	dn.selling_price_list = price_list
	dn.posting_date = frappe.utils.nowdate()

	for item in items:
		wo_name = item.get("work_order")
		transfer_qty = flt(item.get("transfer_qty"))
		
		if transfer_qty <= 0:
			continue

		wo = frappe.get_doc("Work Order", wo_name)
		item_details = frappe.db.get_value("Item", wo.production_item, ["stock_uom", "description", "item_name"], as_dict=1)

		dn.append("items", {
			"item_code": wo.production_item,
			"item_name": item_details.item_name,
			"description": item_details.description,
			"qty": transfer_qty,
			"uom": item_details.stock_uom,
			"warehouse": wo.fg_warehouse,
			"cost_center": frappe.get_cached_value("Company", source_company, "cost_center") or frappe.get_cached_value("Item", wo.production_item, "default_cost_center"),
			"allow_zero_valuation_rate": 1,
			"custom_work_order": wo_name
		})

	if not dn.items:
		frappe.throw(_("No items to transfer"))

	dn.set_missing_values()
	dn.save()
	dn.submit()

	from erpnext.stock.doctype.delivery_note.delivery_note import make_inter_company_purchase_receipt, make_sales_invoice
	
	si = make_sales_invoice(dn.name)
	si.insert(ignore_mandatory=True, ignore_permissions=True)
	si.submit()

	pr = make_inter_company_purchase_receipt(dn.name)
	pr.insert(ignore_mandatory=True, ignore_permissions=True)

	msg = _("Delivery Note {0} and Sales Invoice {1} created and submitted. Purchase Receipt {2} created as Draft.").format(
		f'<a href="/app/delivery-note/{dn.name}" target="_blank">{dn.name}</a>',
		f'<a href="/app/sales-invoice/{si.name}" target="_blank">{si.name}</a>',
		f'<a href="/app/purchase-receipt/{pr.name}" target="_blank">{pr.name}</a>'
	)

	return msg
