frappe.ui.form.on("Production Plan", {
	onload: function (frm) {
		frm.set_query("custom_production_plan_template", function () {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
	},
	custom_production_plan_template: function (frm) {
		if (frm.doc.custom_production_plan_template) {
			frappe.db.get_doc("Production Plan Template", frm.doc.custom_production_plan_template)
				.then(function (template_doc) {
					console.log("Fetched Template:", template_doc);
					frm.set_value("custom__skip_material_transfer_to_wip_warehouse", template_doc.skip_material_transfer_to_wip_warehouse);
					frm.clear_table("po_items");

					template_doc.po_items.forEach(function (item) {
						let row = frm.add_child("po_items");
						row.item_code = item.item;
						row.planned_qty = item.planned_qty;
						row.warehouse = item.finished_goods_warehouse;
					});

					frm.refresh_field("po_items");

					frm.doc.po_items.forEach(function(row) {
                        if (row.item_code) {
                            frappe.call({
                                method: "erpnext.manufacturing.doctype.production_plan.production_plan.get_item_data",
                                args: { item_code: row.item_code },
                                callback: function(r) {
                                    for (let key in r.message) {
                                        frappe.model.set_value(row.doctype, row.name, key, r.message[key]);
                                    }
                                }
                            });
                        }
                    });
				});
		}
	}
});
