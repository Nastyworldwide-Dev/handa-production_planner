import frappe
from erpnext.controllers.stock_controller import make_quality_inspections


def after_insert(doc, method):
	"""
	Automatically create Quality Inspections for finished items
	in a Stock Entry after it is inserted.
	"""
	if doc.inspection_required:
		for item in doc.items:
			# Only consider finished items
			if item.is_finished_item:
				inspections = make_quality_inspections(doc.doctype, doc.name, [{
					"item_code": item.item_code,
					"item_name": item.item_name,
					"qty": item.qty,
					"description": item.description,
					"serial_no": item.serial_no,
					"batch_no": item.batch_no,
					"child_row_reference": item.name,
				}])
				item.quality_inspection = inspections[0]
		doc.save(ignore_permissions=True)
