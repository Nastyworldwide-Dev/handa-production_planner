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
			"fieldtype": "MultiSelectList",
			"options": [
				{ value: "Pending", description: "" },
				{ value: "In Progress", description: "" },
				{ value: "Ready For QC", description: "" },
				{ value: "QC Rejected", description: "" },
				{ value: "Completed", description: "" },
			],
			"default": ""
		}
	],
	get_datatable_options(options) {
		delete options['cellHeight'];
		return Object.assign(options, {
			dynamicRowHeight: true,
			checkboxColumn: true,
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
		report.page.add_inner_button(__("Inter Company Transfer"), function () {
			const selected_rows = report.get_checked_items();
			if (selected_rows.length === 0) {
				frappe.msgprint(__("Please select at least one row."));
				return;
			}

			// Filter for Completed status
			const non_completed = selected_rows.filter(row => row.status !== "Completed");
			if (non_completed.length > 0) {
				frappe.msgprint(__("Only Work Orders with status 'Completed' can be transferred."));
				return;
			}

			// Open Dialog
			const d = new frappe.ui.Dialog({
				title: __('Inter Company Transfer'),
				fields: [
					{
						label: __('Target Company'),
						fieldname: 'target_company',
						fieldtype: 'Link',
						options: 'Company',
						reqd: 1,
						get_query: function () {
							return {
								filters: {
									name: ['!=', report.get_filter_value('company')]
								}
							};
						}
					},
					{
						label: __('Price List'),
						fieldname: 'price_list',
						fieldtype: 'Link',
						options: 'Price List',
						reqd: 1
					},
					{
						label: __('Items'),
						fieldname: 'items',
						fieldtype: 'Table',
						fields: [
							{
								label: __('Work Order'),
								fieldname: 'work_order',
								fieldtype: 'Link',
								options: 'Work Order',
								in_list_view: 1,
								read_only: 1
							},
							{
								label: __('Item Code'),
								fieldname: 'item_code',
								fieldtype: 'Link',
								options: 'Item',
								in_list_view: 1,
								read_only: 1
							},
							{
								label: __('Produced Qty'),
								fieldname: 'produced_qty',
								fieldtype: 'Float',
								in_list_view: 1,
								read_only: 1
							},
							{
								label: __('Transfer Qty'),
								fieldname: 'transfer_qty',
								fieldtype: 'Float',
								in_list_view: 1,
								reqd: 1
							}
						],
						data: selected_rows.map(row => ({
							work_order: row.work_order,
							item_code: row.item_code,
							produced_qty: row.produced_qty,
							transfer_qty: row.produced_qty
						}))
					}
				],
				primary_action_label: __('Create Delivery Note'),
				primary_action: function (values) {
					frappe.call({
						method: 'production_planner.production_planner.report.production_order.production_order.make_inter_company_transfer',
						args: {
							items: values.items,
							target_company: values.target_company,
							source_company: report.get_filter_value('company'),
							price_list: values.price_list
						},
						freeze: true,
						callback: function (r) {
							d.hide();
							if (r.message) {
								frappe.msgprint(r.message);
							}
						}
					});
				}
			});
			d.show();
		});

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
				args: { action, order_no },
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
