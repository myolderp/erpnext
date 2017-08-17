// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
/*
--------------------------------------------------------------------------------------------------------------------------
Version          Author          CreatedOn          ModifiedOn          Remarks
------------ --------------- ------------------ -------------------  -----------------------------------------------------
1.0		  		 SHIV            2017/08/17         					View -> Project option added
--------------------------------------------------------------------------------------------------------------------------                                                                          
*/
frappe.provide("erpnext.projects");

cur_frm.add_fetch("project", "company", "company");

frappe.ui.form.on("Task", {
	refresh: function(frm) {
		var doc = frm.doc;
		if(doc.__islocal) {
			if(!frm.doc.exp_end_date) {
				frm.set_value("exp_end_date", frappe.datetime.add_days(new Date(), 7));
			}
		}


		if(!doc.__islocal) {
			// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
			// Follwoing view option added by SHIV on 2017/08/17
			if(frappe.model.can_read("Project")) {
				frm.add_custom_button(__("Project"), function() {
					frappe.route_options = {"name": doc.project}
					frappe.set_route("Form", "Project", doc.project);
				}, __("View"), true);
			}			
			// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++
			if(frappe.model.can_read("Timesheet")) {
				frm.add_custom_button(__("Timesheet"), function() {
					frappe.route_options = {"project": doc.project, "task": doc.name}
					frappe.set_route("List", "Timesheet");
				}, __("View"), true);
			}
			
			// ++++++++++++++++++++ Ver 1.0 BEGINS ++++++++++++++++++++
			// Following button is removed by SHIV on 2017/08/17
			/*
			if(frappe.model.can_read("Expense Claim")) {
				frm.add_custom_button(__("Expense Claims"), function() {
					frappe.route_options = {"project": doc.project, "task": doc.name}
					frappe.set_route("List", "Expense Claim");
				}, __("View"), true);
			}
			*/
			// +++++++++++++++++++++ Ver 1.0 ENDS +++++++++++++++++++++
			
			if(frm.perm[0].write) {
				if(frm.doc.status!=="Closed" && frm.doc.status!=="Cancelled") {
					frm.add_custom_button(__("Close"), function() {
						frm.set_value("status", "Closed");
						frm.save();
					});
				} else {
					frm.add_custom_button(__("Reopen"), function() {
						frm.set_value("status", "Open");
						frm.save();
					});
				}
			}
		}
	},

	setup: function(frm) {
		frm.fields_dict.project.get_query = function() {
			return {
				query: "erpnext.projects.doctype.task.task.get_project"
			}
		};
	},

	project: function(frm) {
		if(frm.doc.project) {
			return get_server_fields('get_project_details', '','', frm.doc, frm.doc.doctype,
				frm.doc.name, 1);
		}
	},

	validate: function(frm) {
		frm.doc.project && frappe.model.remove_from_locals("Project",
			frm.doc.project);
	},

});

cur_frm.add_fetch('task', 'subject', 'subject');
