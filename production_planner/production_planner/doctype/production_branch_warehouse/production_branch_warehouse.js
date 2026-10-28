// Copyright (c) 2026, Invento Software Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Production Branch Warehouse", {
	setup(frm) {
		frm.set_query("parent_warehouse", () => ({
			filters: { company: frm.doc.company, is_group: 1 },
		}));

		["source_warehouse", "wip_warehouse", "fg_warehouse", "wastage_warehouse"].forEach((field) => {
			frm.set_query(field, () => {
				const filters = { company: frm.doc.company, is_group: 0 };
				if (frm.doc.parent_warehouse) {
					filters.name = ["descendants of", frm.doc.parent_warehouse];
				}
				return { filters };
			});
		});
	},
});
