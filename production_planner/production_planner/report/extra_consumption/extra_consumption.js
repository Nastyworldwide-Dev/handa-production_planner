// Copyright (c) 2025, Invento Software Limited and contributors
// For license information, please see license.txt

frappe.query_reports["Extra Consumption"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "consumption_reason",
			label: __("Consumption Reason"),
			fieldtype: "Link",
			options: "Consumption Reason"
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
        value = default_formatter(value, row, column, data);

        // Add view button only for parent (group) rows
        if (column.fieldname === "description" && data.is_group) {
            value = ` <button class="btn btn-xs btn-info view-reason" data-reason="${encodeURIComponent(data.description || '')}">
                          <i class="fa fa-eye"></i> View
                       </button>`;
        }

        return value;
    },

    onload: function (report) {
        // Handle dialog open on button click
        report.page.body.on("click", ".view-reason", function () {
            const desc = decodeURIComponent($(this).data("reason")) || "No description available";
            const d = new frappe.ui.Dialog({
                title: __("Reason Description"),
                fields: [
                    {
                        fieldtype: "HTML",
                        fieldname: "html",
                        options: `<div style="white-space: pre-line;">${desc}</div>`
                    }
                ],
                primary_action_label: __("Close"),
                primary_action: () => d.hide()
            });
            d.show();
        });
    }
};
