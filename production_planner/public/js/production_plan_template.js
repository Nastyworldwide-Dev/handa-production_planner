frappe.ui.form.on("Production Plan Template", {
	onload: function (frm) {
		frm.set_query("custom_branch", production_planner.branch_query(frm));

		["custom_source_warehouse", "custom_wip_warehouse", "custom_finished_goods_warehouse"].forEach(function (field) {
			frm.set_query(field, production_planner.branch_warehouse_query(frm));
		});
		["finished_goods_warehouse", "custom_source_warehouse", "custom_wip_warehouse"].forEach(function (field) {
			frm.set_query(field, "po_items", production_planner.branch_warehouse_query(frm));
		});
	},

	company: function (frm) {
		if (frm.doc.custom_branch) {
			frm.set_value("custom_branch", "");
		}
	},

	custom_branch: function (frm) {
		return production_planner.apply_branch_warehouses(frm);
	},

	custom_wip_warehouse: function (frm) {
		$.each(frm.doc.po_items || [], function (i, d) {
			d.custom_wip_warehouse = frm.doc.custom_wip_warehouse;
		});
		frm.refresh_field("po_items");
	},
	custom_finished_goods_warehouse: function (frm) {
		$.each(frm.doc.po_items || [], function (i, d) {
			d.finished_goods_warehouse = frm.doc.custom_finished_goods_warehouse;
		});
		frm.refresh_field("po_items");
	},

	custom_source_warehouse: function (frm) {
		$.each(frm.doc.po_items || [], function (i, d) {
			d.custom_source_warehouse = frm.doc.custom_source_warehouse;
		});
		frm.refresh_field("po_items");
	}
});

frappe.ui.form.on("Production Plan Template Items", {
	item: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (frm.doc.custom_wip_warehouse) {
			row.custom_wip_warehouse = frm.doc.custom_wip_warehouse;
			refresh_field("custom_wip_warehouse", cdn, "po_items");
		} else {
			frm.script_manager.copy_from_first_row("po_items", row, ["custom_wip_warehouse"]);
		};

		if (frm.doc.custom_source_warehouse) {
			row.custom_source_warehouse = frm.doc.custom_source_warehouse;
			refresh_field("custom_source_warehouse", cdn, "po_items");
		} else {
			frm.script_manager.copy_from_first_row("po_items", row, ["custom_source_warehouse"]);
		}

		if (frm.doc.custom_finished_goods_warehouse && !row.finished_goods_warehouse) {
			row.finished_goods_warehouse = frm.doc.custom_finished_goods_warehouse;
			refresh_field("finished_goods_warehouse", cdn, "po_items");
		}
	},

	custom_wip_warehouse: function (frm, cdt, cdn) {
		if (!frm.doc.custom_wip_warehouse) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "po_items", "custom_wip_warehouse");
		}
	},

	custom_source_warehouse: function (frm, cdt, cdn) {
		if (!frm.doc.custom_source_warehouse) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "po_items", "custom_source_warehouse");
		}
	}
});