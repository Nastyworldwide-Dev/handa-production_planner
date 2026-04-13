frappe.ui.form.on("Stock Entry", {
	stock_entry_type: function (frm) {
		if (frm.doc.stock_entry_type === "Wastage Entry") {
			// Enable Basic Rate editing for Wastage Entry
			frm.fields_dict.items.grid.update_docfield_property("basic_rate", "read_only", 0);

			// Automatically set the expense account from company settings for existing items
			if (frm.doc.company) {
				frappe.db.get_value("Company", frm.doc.company, "custom_stock_wastage_account", (r) => {
					if (r && r.custom_stock_wastage_account) {
						frm.doc.items.forEach((item) => {
							if (!item.expense_account) {
								frappe.model.set_value(item.doctype, item.name, "expense_account", r.custom_stock_wastage_account);
							}
						});
					}
				});
			}
		}
	},

	refresh: function (frm) {
		if (frm.doc.stock_entry_type === "Wastage Entry") {
			frm.fields_dict.items.grid.update_docfield_property("basic_rate", "read_only", 0);
		}
	}
});
