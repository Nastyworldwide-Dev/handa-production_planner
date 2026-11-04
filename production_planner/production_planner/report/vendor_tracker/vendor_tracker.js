// Copyright (c) 2026, Invento Software Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Vendor Tracker"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "process_type",
			label: __("Process Type"),
			fieldtype: "Select",
			options: "\nMaceration\nCopack"
		},
		{
			fieldname: "vendor",
			label: __("Vendor Site"),
			fieldtype: "Link",
			options: "Production Branch Warehouse"
		},
		{
			fieldname: "item_code",
			label: __("Item"),
			fieldtype: "Link",
			options: "Item"
		},
		{
			fieldname: "timing",
			label: __("Timing"),
			fieldtype: "Select",
			options: "\nNot Sent\nNo Lead Time\nOn Track\nDue Soon\nOverdue\nReceived On Time\nReceived Late\nReceived"
		},
		{
			fieldname: "open_only",
			label: __("Open Jobs Only"),
			fieldtype: "Check",
			default: 1
		}
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "timing" && data && data.timing) {
			const colors = { "Overdue": "red", "Received Late": "orange", "Due Soon": "orange",
				"On Track": "blue", "Received On Time": "green" };
			return `<span class="indicator-pill ${colors[data.timing] || "gray"}">${value}</span>`;
		}
		if (column.fieldname === "days_left" && data && data.days_left < 0) {
			return `<span class="text-danger">${value}</span>`;
		}
		return value;
	}
};
