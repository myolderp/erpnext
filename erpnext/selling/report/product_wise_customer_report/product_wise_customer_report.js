// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Product Wise Customer Report"] = {
	"filters": [
		 {
                        "fieldname": "company",
                        "label": ("Company"),
                        "fieldtype": "Link",
                        "options": "Company",
                        "default": frappe.defaults.get_user_default("Company"),
                        "reqd": 1
                 },
                 {
                        "fieldname": "cost_center",
                        "label": ("Parent Branch"),
                        "fieldtype": "Link",
                        "options": "Cost Center",
                        "get_query": function() {
                                var company = frappe.query_report.filters_by_name.company.get_value();
                                return {
                                        'doctype': "Cost Center",
                                        'filters': [
                                                ['is_disabled', '!=', '1'],
                                                ['company', '=', company]
                                        ]
                                }
                        },
			 "on_change": function(query_report) {
                                var cost_center = query_report.get_values().cost_center;
                                query_report.filters_by_name.branch.set_input(null);
                                query_report.filters_by_name.location.set_input(null);
                                query_report.trigger_refresh();
                                if (!cost_center) {
                                        return;
                                }
                        frappe.call({
                                        method: "erpnext.custom_utils.get_branch_from_cost_center",
                                        args: {
                                                "cost_center": cost_center,
                                        },
                                        callback: function(r) {
                                                query_report.filters_by_name.branch.set_input(r.message)
                                                query_report.trigger_refresh();
                                        }
                                })
                        },
                        "reqd": 1,
                },
		{
                        "fieldname": "branch",
                        "label": ("Branch"),
                        "fieldtype": "Link",
                        "options": "Branch",
                        "read_only": 1,
                        "get_query": function() {
                                var company = frappe.query_report.filters_by_name.company.get_value();
                                return {"doctype": "Branch", "filters": {"company": company, "is_disabled": 0}}
                        }
                },
                {
                        "fieldname": "location",
                        "label": ("Location"),
                        "fieldtype": "Link",
                        "options": "Location",
                        "get_query": function() {
                                var branch = frappe.query_report.filters_by_name.branch.get_value();
                                return {"doctype": "Location", "filters": {"branch": branch, "is_disabled": 0}}
                        }
                },
		{
                        "fieldname": "from_date",
                        "label": __("From Date"),
                        "fieldtype": "Date",
                        "default": frappe.defaults.get_user_default("year_start_date"),
                        "reqd": 1,
                },
                {
                        "fieldname": "to_date",
                        "label": __("To Date"),
                        "fieldtype": "Date",
                        "default": frappe.defaults.get_user_default("year_end_date"),
                        "reqd": 1,
                },
		{
                        "fieldtype": "Break",
                },
		
		{
                        "fieldname": "item_group",
                        "label": ("Material Group"),
                        "fieldtype": "Link",
                        "options": "Item Group",
                        "get_query": function() {
                                return {"doctype": "Item Group", "filters": {"is_group": 0, "is_production_group": 1}}
                        },
                },
                {
                        "fieldname": "item_sub_group",
                        "label": ("Material Sub Group"),
                        "fieldtype": "Link",
                        "options": "Item Sub Group",
                        "get_query": function() {
                                var item_group = frappe.query_report.filters_by_name.item_group.get_value();
                                return {"doctype": "Item Sub Group", "filters": {"item_group": item_group}}
                        }
                },
                {
                        "fieldname": "item",
                        "label": ("Material"),
                        "fieldtype": "Link",
                        "options": "Item",
                        "get_query": function() {
                                var sub_group = frappe.query_report.filters_by_name.item_sub_group.get_value();
                                return {"doctype": "Item", "filters": {"item_sub_group": sub_group, "is_production_item": 1}}
                        }
                },

	]
}