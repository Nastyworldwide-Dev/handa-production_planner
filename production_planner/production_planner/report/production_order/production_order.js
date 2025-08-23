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

    onload: function(report) {
        report.page.wrapper.on("click", ".action-btn", function () {
            let action = $(this).attr("data-action");
            let order_no = $(this).attr("data-order");

            frappe.msgprint({
                title: __("Action Triggered"),
                message: __("You clicked <b>{0}</b> for Order <b>{1}</b>", [action, order_no]),
                indicator: "blue"
            });

            // Example server call (uncomment to use)
            /*
            frappe.call({
                method: "your_app.your_module.report.production_order.production_order.handle_action",
                args: { action, order_no },
                callback: function(r) {
                    frappe.msgprint("Action executed: " + action);
                }
            });
            */
        });
    }
};
