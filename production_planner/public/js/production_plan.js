frappe.ui.form.on("Production Plan", {
	onload: function (frm) {
		frm.set_query("custom_production_plan_template", function () {
			return {
				filters: {
					company: frm.doc.company
				}
			};
		});
		frm.set_query("custom_branch", production_planner.branch_query(frm));

		Object.keys(production_planner.BRANCH_WAREHOUSE_FIELDS).forEach(function (field) {
			frm.set_query(field, production_planner.branch_warehouse_query(frm));
		});
		["warehouse", "custom_source_warehouse", "custom_wip_warehouse"].forEach(function (field) {
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

	custom_production_plan_template: async function (frm) {
		if (!frm.doc.custom_production_plan_template) {
			return;
		}

		const template_doc = await frappe.db.get_doc("Production Plan Template", frm.doc.custom_production_plan_template);
		console.info("[production_plan] Loading template:", { template: template_doc.name, branch: template_doc.custom_branch });
		if (template_doc.company !== frm.doc.company) {
			frappe.msgprint(__("Template {0} belongs to {1}, not {2}.", [template_doc.name, template_doc.company, frm.doc.company]));
			return;
		}
		await frm.set_value("custom__skip_material_transfer_to_wip_warehouse", template_doc.skip_material_transfer_to_wip_warehouse);

		// The template's branch decides the header warehouses; without one, the template's own do.
		// Apply explicitly: set_value skips the trigger when the branch is unchanged.
		if (template_doc.custom_branch) {
			await frm.set_value("custom_branch", template_doc.custom_branch);
			await production_planner.apply_branch_warehouses(frm);
		} else {
			await frm.set_value({
				custom_branch: "",
				custom_wip_warehouse: template_doc.custom_wip_warehouse,
				custom_source_warehouse: template_doc.custom_source_warehouse,
				custom_finished_goods_warehouse: template_doc.custom_finished_goods_warehouse
			});
		}

		frm.clear_table("po_items");

		template_doc.po_items.forEach(function (item) {
			let row = frm.add_child("po_items");
			row.item_code = item.item;
			row.planned_qty = item.planned_qty;
			row.warehouse = item.finished_goods_warehouse || frm.doc.custom_finished_goods_warehouse;
			if (frm.doc.custom_wip_warehouse) {
				row.custom_wip_warehouse = frm.doc.custom_wip_warehouse;
			}
			if (frm.doc.custom_source_warehouse) {
				row.custom_source_warehouse = frm.doc.custom_source_warehouse;
			}
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
				// Rows added here skip the item_code fetch, so item_name needs setting by hand.
				frappe.db.get_value("Item", row.item_code, "item_name").then(function (r) {
					frappe.model.set_value(row.doctype, row.name, "item_name", r.message.item_name);
				});
			}
		});
	},

	custom_wip_warehouse: function (frm) {
		$.each(frm.doc.po_items || [], function (i, d) {
			d.custom_wip_warehouse = frm.doc.custom_wip_warehouse;
		});
		frm.refresh_field("po_items");
	},

	custom_finished_goods_warehouse: function (frm) {
		$.each(frm.doc.po_items || [], function (i, d) {
			d.warehouse = frm.doc.custom_finished_goods_warehouse;
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

frappe.ui.form.on("Production Plan Item", {
	item_code: function (frm, cdt, cdn) {
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
		};

		if (frm.doc.custom_finished_goods_warehouse && !row.warehouse) {
			row.warehouse = frm.doc.custom_finished_goods_warehouse;
			refresh_field("warehouse", cdn, "po_items");
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