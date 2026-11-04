"""Pure rules for the two-stage vendor flow, importable without a bench.

The brand owns every unit of stock. A Production Plan sends materials to an
outside vendor and books what comes back:

    Maceration plan:  raw materials  -> At Macerator (WIP) -> bulk liquid
    Copack plan:      liquid + packs -> At Co-packer (WIP) -> finished product

The Work Order workflow keeps its original state names ("Pending",
"Completed", ...) because those Workflow State records are shared with other
ERPNext workflows. This module maps them to the vendor wording users see, and
holds the lead-time timer and the materials list maths.
"""

import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

PROCESS_TYPES = ("Maceration", "Copack")

# Days before the expected ready date at which an open job counts as "Due Soon".
DUE_SOON_DAYS = 7

STATUS_LABELS = {
	"Pending": "Planned",
	"In Progress": "At Vendor",
	"Ready For QC": "Awaiting QC",
	"QC Rejected": "Rejected",
	"Completed": "Received",
}

SEND = "Send to Vendor"
RETURNED = "Returned from Vendor"
REWORK = "Rework Done"
QC = "Accept / Reject"

ACTIONS_BY_STATUS = {
	"Pending": SEND,
	"In Progress": RETURNED,
	"Ready For QC": QC,
	"QC Rejected": REWORK,
}

# Restaurant-era button names, still accepted from a browser running old JS.
ACTION_ALIASES = {
	"Start": SEND,
	"Prepared": RETURNED,
	"Reprepared": REWORK,
}


def status_label(internal_status):
	"""User-facing label for a Work Order Flow state."""
	return STATUS_LABELS.get(internal_status, internal_status)


def action_for_status(internal_status):
	"""Button shown in Production Order for a state, or "" when there is none."""
	return ACTIONS_BY_STATUS.get(internal_status, "")


def normalize_action(action):
	"""Map old and new button names to the current action, rejecting anything else."""
	action = ACTION_ALIASES.get(action, action)
	if action not in (SEND, RETURNED, REWORK):
		logger.warning("[vendor_flow] unknown action %r", action)
		raise ValueError(f"Unknown action: {action}")
	return action


def expected_ready_date(sent_on, lead_time_days):
	"""Date the vendor should return the job, or None without both inputs."""
	if not sent_on or not lead_time_days:
		return None
	return sent_on + timedelta(days=int(lead_time_days))


def actual_days(sent_on, received_on):
	"""Calendar days the job spent at the vendor, or None until it is back."""
	if not sent_on or not received_on:
		return None
	return (received_on - sent_on).days


def days_left(expected_on, today):
	"""Days until the expected ready date; negative once it has passed."""
	if not expected_on:
		return None
	return (expected_on - today).days


def timing_state(sent_on, expected_on, received_on, today, due_soon_days=DUE_SOON_DAYS):
	"""Where a job stands against its lead time."""
	if received_on:
		if not expected_on:
			return "Received"
		return "Received On Time" if received_on <= expected_on else "Received Late"
	if not sent_on:
		return "Not Sent"
	if not expected_on:
		return "No Lead Time"

	left = days_left(expected_on, today)
	if left < 0:
		return "Overdue"
	if left <= due_soon_days:
		return "Due Soon"
	return "On Track"


def average_actual_days(rows):
	"""Average actual days per (bom_no, vendor), from jobs that have come back.

	Used to compare the BOM's planned lead time with what vendors really take,
	so the lead time on the BOM can be corrected over time.
	"""
	totals = {}
	for row in rows:
		days = row.get("actual_days")
		if days is None:
			continue
		key = (row.get("bom_no"), row.get("vendor"))
		count, total = totals.get(key, (0, 0))
		totals[key] = (count + 1, total + days)

	averages = {key: round(total / count, 1) for key, (count, total) in totals.items()}
	logger.debug("[vendor_flow] lead time history for %s BOM/vendor pairs", len(averages))
	return averages


def material_requirements(lines):
	"""Total required quantity per (item, warehouse), in first-seen order.

	Each line is one BOM component for one plan row: `qty_per_unit` is the BOM
	quantity per unit of the finished item and `planned_qty` the plan row's qty.
	"""
	merged = {}
	for line in lines:
		key = (line["item_code"], line.get("warehouse"))
		required = float(line.get("qty_per_unit") or 0) * float(line.get("planned_qty") or 0)
		if key in merged:
			merged[key]["required_qty"] += required
			continue
		merged[key] = {
			"item_code": line["item_code"],
			"item_name": line.get("item_name"),
			"uom": line.get("uom"),
			"warehouse": line.get("warehouse"),
			"required_qty": required,
		}

	logger.debug("[vendor_flow] %s BOM lines merged into %s materials", len(lines), len(merged))
	return list(merged.values())


def apply_availability(requirements, available):
	"""Add available and shortage quantities; `available` maps (item, warehouse) to qty."""
	result = []
	for req in requirements:
		on_hand = float(available.get((req["item_code"], req.get("warehouse")), 0) or 0)
		required = float(req.get("required_qty") or 0)
		result.append(
			{
				**req,
				"available_qty": on_hand,
				"shortage_qty": max(required - on_hand, 0.0),
			}
		)
	return result


def resolve_source_warehouse(bom_line_source, row_source, header_source):
	"""Where a component is drawn from: BOM line, else plan row, else plan header.

	A copack BOM takes bulk liquid from one store and bottles from another, so a
	source warehouse set on the BOM line wins over the plan's single Source.
	"""
	return bom_line_source or row_source or header_source or None
