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
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nPending\nIn Progress\nReady For QC\nQC Rejected\nCompleted",
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
			if (value === "Accept / Reject" && frappe.user.has_role("QC")) {
				return `
                <button class="btn btn-xs btn-success action-btn"
                    data-action="Accept"
                    data-order="${data.order_number}"
                    data-item="${data.item_code}">
                    Accept
                </button>
                <button class="btn btn-xs btn-danger action-btn"
                    data-action="Reject"
                    data-order="${data.order_number}"
                    data-item="${data.item_code}">
                    Reject
                </button>`;
			} else if (["Start", "Prepared", "Reprepared"].includes(value) && frappe.user.has_role("Chef")) {
				const colorMap = {
					"Start": "btn-primary",
					"Prepared": "btn-info",
					"Reprepared": "btn-warning"
				};

				let btnClass = colorMap[value] || "btn-secondary";

				return `<button class="btn btn-xs ${btnClass} action-btn"
					data-action="${value}" data-order="${data.order_number}">
					${value}
				</button>`;
			} else {
				return "";
			}
		}

		return default_formatter(value, row, column, data);
	},

	onload: function (report) {
		report.page.body.on("click", ".action-btn", function () {
			const action = $(this).attr("data-action");
			const order_no = $(this).attr("data-order");
			const item = $(this).attr("data-item");

			if (!action || !order_no) {
				frappe.msgprint("Action or Order number missing");
				return;
			}

			if (action === "Accept" || action === "Reject") {
				let status = action === "Accept" ? "Accepted" : "Rejected";
				qualityDialog(order_no, report, item || "", status);
				return;
			}

			frappe.call({
				method: "production_planner.production_planner.report.production_order.production_order.handle_action",
				args: {action, order_no},
				callback: function (r) {
					if (r.message) {
						frappe.show_alert({
							message: __(r.message.message),
							indicator: 'green'
						}, 5);
						report.refresh();
					}
				}
			});
		});
	}

};

function qualityDialog(order_no, report, item, status) {
	const dialog = new frappe.ui.Dialog({
		title: "New Quality Inspection",
		fields: [
			{
				label: "Checking Date",
				fieldname: "report_date",
				fieldtype: "Date",
				default: frappe.datetime.get_today(),
				reqd: 1
			},
			{
				label: "Status",
				fieldname: "status",
				fieldtype: "Select",
				options: ["Accepted", "Rejected"],
				default: status,
				reqd: 1,
				read_only: 1,
			},
			{
				label: "Item Code",
				fieldname: "item_code",
				fieldtype: "Link",
				options: "Item",
				default: item,
				reqd: 1,
				read_only: 1,
			},
			{
				label: "Sample Size",
				fieldname: "sample_size",
				fieldtype: "Float",
				default: 0,
				reqd: 1
			},
			{
				label: "Inspected By",
				fieldname: "inspected_by",
				fieldtype: "Link",
				options: "User",
				default: frappe.session.user,
				reqd: 1,
			},
			{
				label: "Remarks",
				fieldname: "remarks",
				fieldtype: "Small Text"
			}
		],
		primary_action_label: "Save",
		primary_action: function (values) {
			frappe.call({
				method: "production_planner.production_planner.report.production_order.production_order.create_quality_inspection",
				args: {
					order_no: order_no,
					data: values
				},
				callback: function (r) {
					let indicator = ""
					if (values.status === "Accepted") {
						indicator = "green"
					} else if (values.status === "Rejected") {
						indicator = "red"
					} else {
						indicator = "yellow"
					}
					if (r.message) {
						frappe.show_alert({
							message: __(r.message.message),
							indicator: indicator
						}, 5);
						report.refresh();
						dialog.hide();
					}
				}
			});
		}
	});
	dialog.show();
}
