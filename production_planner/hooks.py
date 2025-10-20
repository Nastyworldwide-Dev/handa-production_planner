app_name = "production_planner"
app_title = "Production Planner"
app_publisher = "Invento Software Limited"
app_description = "NA"
app_email = "munim@invento.com.bd"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "production_planner",
# 		"logo": "/assets/production_planner/logo.png",
# 		"title": "Production Planner",
# 		"route": "/production_planner",
# 		"has_permission": "production_planner.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/production_planner/css/production_planner.css"
# app_include_js = "/assets/production_planner/js/production_planner.js"

# include js, css files in header of web template
# web_include_css = "/assets/production_planner/css/production_planner.css"
# web_include_js = "/assets/production_planner/js/production_planner.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "production_planner/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "production_planner/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "production_planner.utils.jinja_methods",
# 	"filters": "production_planner.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "production_planner.install.before_install"
# after_install = "production_planner.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "production_planner.uninstall.before_uninstall"
# after_uninstall = "production_planner.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "production_planner.utils.before_app_install"
# after_app_install = "production_planner.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "production_planner.utils.before_app_uninstall"
# after_app_uninstall = "production_planner.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "production_planner.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Production Plan": {
		"on_submit": "production_planner.hook_functions.production_plan.on_submit"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"production_planner.tasks.all"
# 	],
# 	"daily": [
# 		"production_planner.tasks.daily"
# 	],
# 	"hourly": [
# 		"production_planner.tasks.hourly"
# 	],
# 	"weekly": [
# 		"production_planner.tasks.weekly"
# 	],
# 	"monthly": [
# 		"production_planner.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "production_planner.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "production_planner.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "production_planner.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["production_planner.utils.before_request"]
# after_request = ["production_planner.utils.after_request"]

# Job Events
# ----------
# before_job = ["production_planner.utils.before_job"]
# after_job = ["production_planner.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"production_planner.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


fixtures = [
	{"dt": "Workspace",
	 "filters": [["name", "in", ["Chef's Panel", "QC Panel", "Production Panel", "Admin Panel"]]]},
	{"dt": "Workflow"},
	{"dt": "Workflow State"},
	{"dt": "Workflow Action"},
	{"dt": "Role", "filters": [["name", "in", ["Chef", "QC", "Production"]]]},
	{"dt": "Role Profile", "filters": [["name", "in", ["Chef", "QC", "Production", "Admin"]]]},
	{"dt": "Custom DocPerm", "filters": [["role", "in", ["Chef", "QC", "Production"]]]},
	{"dt": "Custom Role"},
]
