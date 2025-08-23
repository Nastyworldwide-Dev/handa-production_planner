# Copyright (c) 2025, Invento Software Limited and contributors
# For license information, please see license.txt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Action", "fieldname": "action", "fieldtype": "Data", "width": 200},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Data", "width": 180},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "Order Qty", "fieldname": "order_qty", "fieldtype": "Int", "width": 100},
        {"label": "Produced Qty", "fieldname": "produced_qty", "fieldtype": "Int", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Order Number", "fieldname": "order_number", "fieldtype": "Data", "width": 200},
    ]


def get_data(filters=None):
    demo_data = [
        {"action": "Start", "item_code": "BKR-AYPCK-1-PCS", "item_name": "AYAM PERCIK", "order_qty": 100, "produced_qty": 0, "status": "Pending", "order_number": "MFG-WO-2025-00011"},
        {"action": "Prepared", "item_code": "BKR-IKBWL-1-PCS", "item_name": "IKAN BAWAL", "order_qty": 20, "produced_qty": 0, "status": "In Progress", "order_number": "MFG-WO-2025-00012"},
        {"action": "Accept / Reject", "item_code": "BKR-IKCCR-1-PCS", "item_name": "IKAN CENCARU", "order_qty": 40, "produced_qty": 0, "status": "Ready for QC", "order_number": "MFG-WO-2025-00013"},
        {"action": "Finish", "item_code": "BKR-IKCCRSBT-1-PCS", "item_name": "IKAN CENCARU SUMBAT", "order_qty": 30, "produced_qty": 0, "status": "QC Approved", "order_number": "MFG-WO-2025-00014"},
        {"action": "", "item_code": "BKR-IKPRI-1-PCS", "item_name": "IKAN PARI", "order_qty": 60, "produced_qty": 60, "status": "Completed", "order_number": "MFG-WO-2025-00015"},
        {"action": "Start", "item_code": "BKR-KRGSBL-1-HDG", "item_name": "KERANG SAMBAL", "order_qty": 100, "produced_qty": 0, "status": "In Progress", "order_number": "MFG-WO-2025-00016"},
        {"action": "", "item_code": "BKR-KPGSBL-1-HDG", "item_name": "KUPANG SAMBAL", "order_qty": 20, "produced_qty": 0, "status": "Completed", "order_number": "MFG-WO-2025-00017"},
        {"action": "Finish", "item_code": "BKR-STYAY-1-HDG", "item_name": "SATAY AYAM", "order_qty": 30, "produced_qty": 0, "status": "QC Approved", "order_number": "MFG-WO-2025-00018"},
        {"action": "Prepared", "item_code": "BKR-STYDG-1-HDG", "item_name": "SATAY DAGING", "order_qty": 40, "produced_qty": 0, "status": "In Progress", "order_number": "MFG-WO-2025-00019"},
        {"action": "Start", "item_code": "BKR-SIASBLPT-1-PCS", "item_name": "SIAKAP SAMBAL PETAI", "order_qty": 50, "produced_qty": 0, "status": "Pending", "order_number": "MFG-WO-2025-00020"}
    ]

    # Apply filters if provided (demo version)
    if filters:
        if filters.get("status"):
            demo_data = [d for d in demo_data if d["status"] == filters["status"]]

    return demo_data
