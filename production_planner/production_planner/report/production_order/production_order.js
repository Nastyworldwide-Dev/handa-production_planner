// Copyright (c) 2025, Invento Software Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Production Order"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nPending\nIn Progress\nReady for QC\nQC Approved\nCompleted",
			"default": ""
		}
	],
	get_datatable_options(options) {
		delete options['cellHeight'];
		return Object.assign(options, {
			dynamicRowHeight: true,
			checkboxColumn: false,
			cellHeight: 36
		});

	},
	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname === "action" && value) {
			// Handle special case for Accept / Reject
			if (value === "Accept / Reject") {
				return `
                    <button class="btn btn-xs btn-success action-btn"
                        data-action="Accept" data-order="${data.order_number}">
                        Accept
                    </button>
                    <button class="btn btn-xs btn-danger action-btn"
                        data-action="Reject" data-order="${data.order_number}">
                        Reject
                    </button>`;
			}

			// Color map for other single-action buttons
			const colorMap = {
				"Start": "btn-primary",     // Blue
				"Prepared": "btn-info",     // Light Blue
				"Finish": "btn-warning"     // Yellow/Orange
			};

			let btnClass = colorMap[value] || "btn-secondary";

			return `<button class="btn btn-xs ${btnClass} action-btn"
                        data-action="${value}" data-order="${data.order_number}">
                        ${value}
                    </button>`;
		}

		return default_formatter(value, row, column, data);
	},

	onload: function (report) {
		report.page.body.on("click", ".action-btn", function () {
			const action = $(this).attr("data-action");
			const order_no = $(this).attr("data-order");

			if (!action || !order_no) {
				frappe.msgprint("Action or Order number missing");
				return;
			}

			frappe.call({
				method: "production_planner.production_planner.report.production_order.production_order.handle_action",
				args: {action, order_no},
				callback: function (r) {
					if (r.message) {
						frappe.msgprint(r.message.message);

						if (!r.message.data.skip_transfer) {
							frappe.xcall("erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry", {
								work_order_id: order_no,
								purpose: "Material Transfer for Manufacture",
								qty: r.message.data.qty,
							}).then((stock_entry) => {
								frappe.model.sync(stock_entry);
								frappe.set_route("Form", stock_entry.doctype, stock_entry.name);
							}).catch((err) => {
								frappe.msgprint("Failed to create Stock Entry: " + err.message);
							});
						}

						report.refresh();
					}
				}
			});
		});
	}

};
