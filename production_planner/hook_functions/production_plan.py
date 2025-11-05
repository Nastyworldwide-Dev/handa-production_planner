import frappe
from frappe import _


def on_submit(doc, method):
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
