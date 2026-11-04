"""Rules for the two-stage vendor flow (maceration, then copack).

The brand sends raw materials to an outside vendor, the vendor returns bulk
liquid (maceration) or finished product (copack), and QC accepts it into stock.
These tests pin the pure rules behind that flow: the lead-time timer, the
user-facing status / action names, and the materials list on the plan.
"""

import unittest
from datetime import date

from production_planner.vendor_flow import (
	ACTION_ALIASES,
	action_for_status,
	actual_days,
	apply_availability,
	average_actual_days,
	days_left,
	expected_ready_date,
	material_requirements,
	normalize_action,
	resolve_source_warehouse,
	status_label,
	timing_state,
)


class TestLeadTimeTimer(unittest.TestCase):
	def test_expected_ready_is_sent_plus_lead_days(self):
		self.assertEqual(expected_ready_date(date(2026, 11, 1), 21), date(2026, 11, 22))

	def test_no_expected_ready_without_lead_time_or_sent_date(self):
		self.assertIsNone(expected_ready_date(date(2026, 11, 1), 0))
		self.assertIsNone(expected_ready_date(date(2026, 11, 1), None))
		self.assertIsNone(expected_ready_date(None, 21))

	def test_actual_days_between_sent_and_received(self):
		self.assertEqual(actual_days(date(2026, 11, 1), date(2026, 11, 25)), 24)
		self.assertIsNone(actual_days(date(2026, 11, 1), None))
		self.assertIsNone(actual_days(None, date(2026, 11, 25)))

	def test_days_left_goes_negative_when_late(self):
		self.assertEqual(days_left(date(2026, 11, 22), date(2026, 11, 20)), 2)
		self.assertEqual(days_left(date(2026, 11, 22), date(2026, 11, 25)), -3)
		self.assertIsNone(days_left(None, date(2026, 11, 25)))


class TestTimingState(unittest.TestCase):
	today = date(2026, 11, 20)

	def test_not_sent(self):
		self.assertEqual(timing_state(None, None, None, self.today), "Not Sent")

	def test_sent_without_lead_time(self):
		self.assertEqual(timing_state(date(2026, 11, 1), None, None, self.today), "No Lead Time")

	def test_on_track_due_soon_overdue(self):
		sent = date(2026, 11, 1)
		self.assertEqual(timing_state(sent, date(2026, 12, 15), None, self.today), "On Track")
		self.assertEqual(timing_state(sent, date(2026, 11, 27), None, self.today), "Due Soon")
		self.assertEqual(timing_state(sent, date(2026, 11, 20), None, self.today), "Due Soon")
		self.assertEqual(timing_state(sent, date(2026, 11, 19), None, self.today), "Overdue")

	def test_received_on_time_or_late(self):
		sent = date(2026, 11, 1)
		expected = date(2026, 11, 22)
		self.assertEqual(timing_state(sent, expected, date(2026, 11, 22), self.today), "Received On Time")
		self.assertEqual(timing_state(sent, expected, date(2026, 11, 24), self.today), "Received Late")
		self.assertEqual(timing_state(sent, None, date(2026, 11, 24), self.today), "Received")


class TestForecast(unittest.TestCase):
	def test_average_actual_days_per_bom_and_vendor(self):
		rows = [
			{"bom_no": "BOM-OUD", "vendor": "Macerator A", "actual_days": 20},
			{"bom_no": "BOM-OUD", "vendor": "Macerator A", "actual_days": 24},
			{"bom_no": "BOM-OUD", "vendor": "Macerator B", "actual_days": 30},
			{"bom_no": "BOM-OUD", "vendor": "Macerator A", "actual_days": None},
		]
		averages = average_actual_days(rows)
		self.assertEqual(averages[("BOM-OUD", "Macerator A")], 22.0)
		self.assertEqual(averages[("BOM-OUD", "Macerator B")], 30.0)

	def test_average_ignores_groups_without_history(self):
		rows = [{"bom_no": "BOM-NEW", "vendor": "X", "actual_days": None}]
		self.assertEqual(average_actual_days(rows), {})


class TestStatusAndActions(unittest.TestCase):
	def test_internal_states_show_vendor_labels(self):
		self.assertEqual(status_label("Pending"), "Planned")
		self.assertEqual(status_label("In Progress"), "At Vendor")
		self.assertEqual(status_label("Ready For QC"), "Awaiting QC")
		self.assertEqual(status_label("QC Rejected"), "Rejected")
		self.assertEqual(status_label("Completed"), "Received")

	def test_action_buttons_per_status(self):
		self.assertEqual(action_for_status("Pending"), "Send to Vendor")
		self.assertEqual(action_for_status("In Progress"), "Returned from Vendor")
		self.assertEqual(action_for_status("Ready For QC"), "Accept / Reject")
		self.assertEqual(action_for_status("QC Rejected"), "Rework Done")
		self.assertEqual(action_for_status("Completed"), "")

	def test_old_restaurant_actions_still_accepted(self):
		# A browser holding the old report JS must keep working until it reloads.
		self.assertEqual(normalize_action("Start"), "Send to Vendor")
		self.assertEqual(normalize_action("Prepared"), "Returned from Vendor")
		self.assertEqual(normalize_action("Reprepared"), "Rework Done")
		self.assertEqual(normalize_action("Send to Vendor"), "Send to Vendor")
		self.assertEqual(set(ACTION_ALIASES), {"Start", "Prepared", "Reprepared"})

	def test_unknown_action_rejected(self):
		with self.assertRaises(ValueError):
			normalize_action("Cook")


class TestMaterialRequirements(unittest.TestCase):
	def test_scales_bom_lines_by_planned_qty_and_merges_duplicates(self):
		lines = [
			# Two plan rows using the same oil from the same warehouse merge into one line.
			{
				"item_code": "OIL-OUD",
				"item_name": "Oud Oil",
				"uom": "ml",
				"qty_per_unit": 0.2,
				"planned_qty": 1000,
				"warehouse": "RM Store - N",
			},
			{
				"item_code": "OIL-OUD",
				"item_name": "Oud Oil",
				"uom": "ml",
				"qty_per_unit": 0.1,
				"planned_qty": 500,
				"warehouse": "RM Store - N",
			},
			{
				"item_code": "ALC-96",
				"item_name": "Perfumer Alcohol",
				"uom": "ml",
				"qty_per_unit": 0.8,
				"planned_qty": 1000,
				"warehouse": "RM Store - N",
			},
		]
		result = material_requirements(lines)
		self.assertEqual([r["item_code"] for r in result], ["OIL-OUD", "ALC-96"])
		self.assertAlmostEqual(result[0]["required_qty"], 250.0)
		self.assertAlmostEqual(result[1]["required_qty"], 800.0)

	def test_same_item_from_different_warehouses_stays_separate(self):
		lines = [
			{
				"item_code": "BTL-50",
				"item_name": "Bottle 50ml",
				"uom": "Nos",
				"qty_per_unit": 1,
				"planned_qty": 10,
				"warehouse": "Packaging - N",
			},
			{
				"item_code": "BTL-50",
				"item_name": "Bottle 50ml",
				"uom": "Nos",
				"qty_per_unit": 1,
				"planned_qty": 5,
				"warehouse": "Spare - N",
			},
		]
		self.assertEqual(len(material_requirements(lines)), 2)

	def test_shortage_against_available_stock(self):
		reqs = [
			{"item_code": "OIL-OUD", "warehouse": "RM Store - N", "required_qty": 250.0},
			{"item_code": "ALC-96", "warehouse": "RM Store - N", "required_qty": 800.0},
		]
		available = {("OIL-OUD", "RM Store - N"): 300.0, ("ALC-96", "RM Store - N"): 500.0}
		result = apply_availability(reqs, available)
		self.assertEqual(result[0]["available_qty"], 300.0)
		self.assertEqual(result[0]["shortage_qty"], 0.0)
		self.assertEqual(result[1]["available_qty"], 500.0)
		self.assertEqual(result[1]["shortage_qty"], 300.0)

	def test_missing_stock_counts_as_zero(self):
		result = apply_availability([{"item_code": "X", "warehouse": "W", "required_qty": 5}], {})
		self.assertEqual(result[0]["available_qty"], 0.0)
		self.assertEqual(result[0]["shortage_qty"], 5.0)


class TestSourceWarehouse(unittest.TestCase):
	"""Copack pulls liquid and packaging from different stores, so the BOM line can override."""

	def test_bom_line_source_wins(self):
		self.assertEqual(
			resolve_source_warehouse("Bulk Liquid - N", "Row Store - N", "Header Store - N"),
			"Bulk Liquid - N",
		)

	def test_falls_back_to_row_then_header(self):
		self.assertEqual(resolve_source_warehouse(None, "Row Store - N", "Header Store - N"), "Row Store - N")
		self.assertEqual(resolve_source_warehouse("", None, "Header Store - N"), "Header Store - N")
		self.assertIsNone(resolve_source_warehouse(None, None, None))


if __name__ == "__main__":
	unittest.main()
