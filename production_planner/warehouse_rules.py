"""Pure rules about warehouses, importable without a bench.

ERPNext writes a Stock Ledger Entry only on submit, and that is the first place
a group (parent-node) warehouse is rejected — see
`erpnext/stock/doctype/stock_ledger_entry/stock_ledger_entry.py`:

    Group node warehouse is not allowed to select for transactions

By then the Production Plan is submitted, the Work Orders exist and the QC user
is clicking Accept. Everything here exists to catch the group node earlier, and
to say which field holds it when it slips through anyway.
"""

import logging

logger = logging.getLogger(__name__)


def group_warehouse_offenders(candidates, group_names):
	"""Return the (label, warehouse) pairs whose warehouse is a group node.

	`candidates` is an iterable of (label, warehouse); blanks are skipped and
	duplicate pairs collapse so a 40-row table reports each mistake once.
	`group_names` is the set of warehouse names known to have is_group = 1.
	"""
	offenders = []
	for label, warehouse in candidates:
		if not warehouse:
			continue
		if warehouse not in group_names:
			continue
		pair = (label, warehouse)
		if pair not in offenders:
			offenders.append(pair)

	if offenders:
		logger.warning("[warehouse_rules] group warehouses selected: %s", offenders)

	return offenders


def group_warehouse_message(offenders):
	"""Human-readable instruction for the offenders, or "" when there are none."""
	if not offenders:
		return ""

	lines = [f"{label}: {warehouse}" for label, warehouse in offenders]
	return (
		"Group node warehouse is not allowed to select for transactions. "
		"Pick a child (non-group) warehouse for:<br><br>" + "<br>".join(lines)
	)


def branch_warehouse_offenders(candidates, branch_warehouses):
	"""Return the (label, warehouse) pairs whose warehouse is outside the branch.

	`branch_warehouses` is the set of warehouse names under the branch's group
	warehouse. Blanks are skipped and duplicate pairs collapse, as above.
	"""
	offenders = []
	for label, warehouse in candidates:
		if not warehouse or warehouse in branch_warehouses:
			continue
		pair = (label, warehouse)
		if pair not in offenders:
			offenders.append(pair)

	if offenders:
		logger.warning("[warehouse_rules] warehouses outside branch: %s", offenders)

	return offenders


def branch_warehouse_message(offenders, branch, parent_warehouse):
	"""Human-readable instruction for the offenders, or "" when there are none."""
	if not offenders:
		return ""

	lines = [f"{label}: {warehouse}" for label, warehouse in offenders]
	return (
		f"Branch {branch} only allows warehouses under {parent_warehouse}. "
		"Pick a warehouse from that branch for:<br><br>" + "<br>".join(lines)
	)


def branch_profile_candidates(profile):
	"""Label/warehouse pairs held by a Production Branch Warehouse profile."""
	return [
		("Source Warehouse", profile.get("source_warehouse")),
		("Work-in-Progress Warehouse", profile.get("wip_warehouse")),
		("Finished Goods Warehouse", profile.get("fg_warehouse")),
		("Wastage Warehouse", profile.get("wastage_warehouse")),
	]


def warehouse_candidates(doc):
	"""Label/warehouse pairs to check on a Production Plan (or its Template)."""
	candidates = [
		("Source Warehouse", doc.get("custom_source_warehouse")),
		("Work-in-Progress Warehouse", doc.get("custom_wip_warehouse")),
		("Finished Goods Warehouse", doc.get("custom_finished_goods_warehouse")),
		("Wastage Warehouse", doc.get("custom_wastage_warehouse")),
	]

	for row in doc.get("po_items") or []:
		idx = row.get("idx")
		candidates.append((f"Row {idx} Source Warehouse", row.get("custom_source_warehouse")))
		candidates.append((f"Row {idx} Work-in-Progress Warehouse", row.get("custom_wip_warehouse")))
		candidates.append((f"Row {idx} Finished Goods Warehouse", row.get("warehouse")))

	return candidates


def stock_entry_candidates(doc):
	"""Label/warehouse pairs to check on a Stock Entry before it is submitted."""
	candidates = [
		("Default Source Warehouse", doc.get("from_warehouse")),
		("Default Target Warehouse", doc.get("to_warehouse")),
	]

	for row in doc.get("items") or []:
		where = f"Row {row.get('idx')} ({row.get('item_code')})"
		candidates.append((f"{where} Source Warehouse", row.get("s_warehouse")))
		candidates.append((f"{where} Target Warehouse", row.get("t_warehouse")))

	return candidates
