// Shared by Production Plan and Production Plan Template: the Branch field picks a
// Production Branch Warehouse, which fills the header warehouses and limits every
// warehouse picker to the branch's group warehouse.
frappe.provide("production_planner");

// Header field on the form -> field on Production Branch Warehouse.
production_planner.BRANCH_WAREHOUSE_FIELDS = {
	custom_source_warehouse: "source_warehouse",
	custom_wip_warehouse: "wip_warehouse",
	custom_finished_goods_warehouse: "fg_warehouse",
	custom_wastage_warehouse: "wastage_warehouse"
};

production_planner.branch_query = function (frm) {
	return function () {
		return {
			filters: {
				company: frm.doc.company
			}
		};
	};
};

// Leaf warehouses of the company, and of the branch once one is picked.
production_planner.branch_warehouse_query = function (frm) {
	return function () {
		const filters = {
			company: frm.doc.company,
			is_group: 0
		};
		if (frm.doc.custom_branch_warehouse) {
			filters.name = ["descendants of", frm.doc.custom_branch_warehouse];
		}
		return { filters: filters };
	};
};

production_planner.apply_branch_warehouses = function (frm) {
	if (!frm.doc.custom_branch) {
		return;
	}

	const fields = Object.keys(production_planner.BRANCH_WAREHOUSE_FIELDS).filter(function (field) {
		return frm.fields_dict[field];
	});
	const source_fields = fields.map(function (field) {
		return production_planner.BRANCH_WAREHOUSE_FIELDS[field];
	});

	return frappe.db.get_value("Production Branch Warehouse", frm.doc.custom_branch, source_fields)
		.then(function (r) {
			const profile = r.message || {};
			const values = {};
			// Blank where the branch has no default, so another branch's warehouse can't linger.
			fields.forEach(function (field) {
				values[field] = profile[production_planner.BRANCH_WAREHOUSE_FIELDS[field]] || "";
			});
			console.info("[branch_warehouse] Applying branch warehouses:", { branch: frm.doc.custom_branch, values: values });
			return frm.set_value(values);
		});
};
