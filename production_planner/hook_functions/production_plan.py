import frappe
from frappe import _


@frappe.whitelist()
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
			if doc.get('custom__skip_material_transfer_to_wip_warehouse'):
				wo_doc.skip_transfer = 1
				wo_doc.save()

	except Exception as e:
		frappe.throw(_("Failed to create or submit Work Orders: {0}").format(e))
