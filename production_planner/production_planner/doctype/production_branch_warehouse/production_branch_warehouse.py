# Copyright (c) 2026, Invento Software Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from production_planner.warehouse_rules import (
	branch_profile_candidates,
	branch_warehouse_message,
	branch_warehouse_offenders,
)


class ProductionBranchWarehouse(Document):
	def validate(self):
		self.validate_parent_warehouse()
		self.validate_default_warehouses()

	def validate_parent_warehouse(self):
		is_group, company = frappe.db.get_value(
			"Warehouse", self.parent_warehouse, ["is_group", "company"]
		)
		if not is_group:
			frappe.throw(
				_("Branch Warehouse {0} must be a group warehouse.").format(self.parent_warehouse)
			)
		if company != self.company:
			frappe.throw(
				_("Branch Warehouse {0} belongs to {1}, not {2}.").format(
					self.parent_warehouse, company, self.company
				)
			)

	def validate_default_warehouses(self):
		offenders = branch_warehouse_offenders(
			branch_profile_candidates(self), get_branch_warehouses(self.parent_warehouse)
		)
		if offenders:
			frappe.logger("production_planner").warning(
				"[production_branch_warehouse] %s blocked, outside %s: %s",
				self.name,
				self.parent_warehouse,
				offenders,
			)
			frappe.throw(
				branch_warehouse_message(offenders, self.branch, self.parent_warehouse),
				title=_("Invalid Warehouse"),
			)


def get_branch_warehouses(parent_warehouse):
	"""Leaf warehouses under `parent_warehouse` in the Warehouse tree."""
	warehouses = frappe.get_all(
		"Warehouse",
		filters={"name": ("descendants of", parent_warehouse), "is_group": 0},
		pluck="name",
	)
	frappe.logger("production_planner").debug(
		"[production_branch_warehouse] %s has %s leaf warehouses", parent_warehouse, len(warehouses)
	)
	return set(warehouses)


def get_branch_profile(company, branch):
	"""The Production Branch Warehouse for company + branch, or None."""
	return frappe.db.get_value(
		"Production Branch Warehouse",
		{"company": company, "branch": branch},
		["name", "parent_warehouse"],
		as_dict=True,
	)
