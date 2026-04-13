import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry

class CustomStockEntry(StockEntry):
	@frappe.whitelist()
	def get_item_details(self, args=None, for_update=False):
		# Call the standard ERPNext get_item_details
		ret = super().get_item_details(args, for_update)

		# If the Stock Entry Type is 'Wastage Entry', use the custom wastage account from Company
		if self.stock_entry_type == "Wastage Entry":
			wastage_account = frappe.db.get_value("Company", self.company, "custom_stock_wastage_account")
			if wastage_account:
				ret["expense_account"] = wastage_account

		return ret
