# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

'''
------------------------------------------------------------------------------------------------------------------------------------------
Version          Author         Ticket#           CreatedOn          ModifiedOn          Remarks
------------ --------------- --------------- ------------------ -------------------  -----------------------------------------------------
3.0               SHIV		                   28/01/2019                          Original Version
------------------------------------------------------------------------------------------------------------------------------------------                                                                          
'''

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.hr.doctype.approver_settings.approver_settings import get_final_approver
from erpnext.hr.hr_custom_functions import get_officiating_employee

def validate_workflow_states(doc):
	approver_field = {
			"Salary Advance": ["advance_approver","advance_approver_name","advance_approver_designation"],
			"Leave Application": ["leave_approver","leave_approver_name"],
			"Travel Authorization": ["supervisor",""],
			"Travel Claim": ["supervisor",""]
	}
	
	if not approver_field.has_key(doc.doctype) or not frappe.db.exists("Workflow", {"document_type": doc.doctype, "is_active": 1}):
		return

	document_approver = approver_field[doc.doctype]
	employee          = frappe.db.get_value("Employee", doc.employee, ["user_id","employee_name","designation","name"])
	reports_to        = frappe.db.get_value("Employee", frappe.db.get_value("Employee", doc.employee, "reports_to"), ["user_id","employee_name","designation","name"])
	final_approver    = frappe.db.get_value("Employee", {"user_id": get_final_approver(doc.branch)}, ["user_id","employee_name","designation","name"])
        workflow_state    = doc.get("workflow_state").lower()

        if doc.doctype == "Salary Advance":
                ''' employee --> final_approver(branch)/reports_to(final_approver(branch)) '''
                if workflow_state == "Draft".lower():
                        vars(doc)[document_approver[0]] = employee[0]
                        vars(doc)[document_approver[1]] = employee[1]
                        vars(doc)[document_approver[2]] = employee[2]
                elif workflow_state == "Waiting Approval".lower():
                        if employee[0] == final_approver[0]:
                                officiating = get_officiating_employee(reports_to[3])
                                if officiating:
                                        officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
                                        
                                vars(doc)[document_approver[0]] = officiating[0] if officiating else reports_to[0]
                                vars(doc)[document_approver[1]] = officiating[1] if officiating else reports_to[1]
                                vars(doc)[document_approver[2]] = officiating[2] if officiating else reports_to[2]
                        else:
                                officiating = get_officiating_employee(final_approver[3])
                                if officiating:
                                        officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])

                                vars(doc)[document_approver[0]] = officiating[0] if officiating else final_approver[0]
                                vars(doc)[document_approver[1]] = officiating[1] if officiating else final_approver[1]
                                vars(doc)[document_approver[2]] = officiating[2] if officiating else final_approver[2]
                elif workflow_state == "Approved".lower():
                        if doc.get(document_approver[0]) != frappe.session.user:
                                frappe.throw(_("Only <b>{0}, {1}</b> can approve this application").format(doc.get(document_approver[2]),doc.get(document_approver[1])), title="Invalid Operation")
                elif workflow_state == "Rejected".lower():
                        if doc.get(document_approver[0]) and doc.get(document_approver[0]) != frappe.session.user:
                                if workflow_state != doc.get_db_value("workflow_state"):
                                        frappe.throw(_("Only <b>{0}, {1}</b> can reject this application").format(doc.get(document_approver[2]),doc.get(document_approver[1])), title="Invalid Operation")
                        #vars(doc)[document_approver[0]] = employee[0]
                        #vars(doc)[document_approver[1]] = employee[1]
                        #vars(doc)[document_approver[2]] = employee[2]
                else:
                        pass
        elif doc.doctype == "Leave Application":
		if workflow_state == "Draft".lower():
			vars(doc)[document_approver[0]] = employee[0]
                        vars(doc)[document_approver[1]] = employee[1]
		elif workflow_state == "Approved".lower():
			if  doc.leave_approver != frappe.session.user:
				frappe.throw("Only {0} can submit the leave application".format(doc.leave_approver))
                        if final_approver[0] != doc.leave_approver and employee[0] != final_approver[0]:
                                frappe.throw("Only {0} can approve your leave application".format(frappe.bold(final_approver[0])))
                        doc.status= "Approved"

		if workflow_state == "Waiting Supervisor Approval".lower():
			officiating = get_officiating_employee(reports_to[3])
			if officiating:
				officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
			vars(doc)[document_approver[0]] = officiating[0] if officiating else reports_to[0]
			vars(doc)[document_approver[1]] = officiating[1] if officiating else reports_to[1]

			if doc.leave_approver == employee[0]:
				frappe.throw("Leave Application submitter {0} cannot be the supervisor ".format(doc.leave_approver))

                elif workflow_state == "Verified By Supervisor".lower():
			if  doc.leave_approver != frappe.session.user:
				frappe.throw("Only {0} can submit the leave application".format(doc.leave_approver))
			if final_approver[0] != employee[0]:
				officiating = get_officiating_employee(final_approver[3])
				if officiating:
                                       	officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
				vars(doc)[document_approver[0]] = officiating[0] if officiating else final_approver[0]
                                vars(doc)[document_approver[1]] = officiating[1] if officiating else final_approver[1]
                elif workflow_state in ['Rejected', 'Rejected By Supervisor']:
                        if workflow_state == "Rejected".lower():
                                doc.status = "Rejected"
                        
			vars(doc)[document_approver[0]] = reports_to[0]
                        vars(doc)[document_approver[1]] = reports_to[1]
                elif workflow_state == "Cancelled".lower():
                        if frappe.session.user not in (doc.leave_approver,"Administrator"):
                                frappe.throw(_("Only leave approver <b>{0}</b> ( {1} ) can cancel this document.").format(doc.leave_approver_name, doc.leave_approver), title="Operation not permitted")
	elif doc.doctype == "Travel Authorization":
		if workflow_state == "Draft".lower():
			vars(doc)[document_approver[0]] = employee[0]

		elif workflow_state == "Waiting Supervisor Approval".lower():
			officiating = get_officiating_employee(reports_to[3])
                        if officiating:
                                officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
                        vars(doc)[document_approver[0]] = officiating[0] if officiating else reports_to[0]
			
			if doc.supervisor == employee[0]:
				frappe.throw("Travel Authorization submitter {0} cannot be the supervisor ".format(doc.supervisor))
			
		elif workflow_state == "Approved".lower():
			if doc.supervisor != frappe.session.user:
				frappe.throw("Only {0} can Approve the Travel Authorization".format(doc.supervisor))
                        if final_approver[0] != doc.supervisor and employee[0] != final_approver[0]:
                                frappe.throw("Only {0} can approve your Travel Authorization".format(frappe.bold(final_approver[0])))
                        doc.status= "Approved"

                elif workflow_state == "Verified By Supervisor".lower():
			if doc.supervisor != frappe.session.user:
				frappe.throw("Only {0} can submit the Travel Authorization".format(doc.supervisor))
			officiating = get_officiating_employee(final_approver[3])
			if officiating:
				officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
			vars(doc)[document_approver[0]] = officiating[0] if officiating else final_approver[0]
			vars(doc)[document_approver[1]] = officiating[1] if officiating else final_approver[1]
		
                elif workflow_state in ['Rejected', 'Rejected By Supervisor']:
                        if workflow_state == "Rejected".lower():
                                doc.status = "Rejected"
			vars(doc)[document_approver[0]] = reports_to[0]
	elif doc.doctype == "Travel Claim":
		hr_user = frappe.db.get_single_value("HR Settings", "hr_approver")
		hr_approver = frappe.db.get_value("Employee", hr_user, ["user_id","employee_name","designation","name"])
		if workflow_state == "Draft".lower():
			vars(doc)[document_approver[0]] = employee[0]

		elif workflow_state == "Waiting Supervisor Approval".lower():
			if doc.place_type == "In-Country":
				officiating = get_officiating_employee(reports_to[3])
				if officiating:
					officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
				vars(doc)[document_approver[0]] = officiating[0] if officiating else reports_to[0]
			elif doc.place_type == "Out-Country":
				officiating = get_officiating_employee(hr_approver[3])
                                if officiating:
                                        officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
                                vars(doc)[document_approver[0]] = officiating[0] if officiating else hr_approver[0]
				
		elif workflow_state == "Approved".lower():
			if doc.supervisor != frappe.session.user:
				frappe.throw("Only {0} can submit the Travel Authorization".format(doc.supervisor))
			if doc.place_type == "In-Country":
				if final_approver[0] != doc.supervisor and employee[0] != final_approver[0]:
					frappe.throw("Only {0} can approve your Travel Authorization".format(frappe.bold(final_approver[0])))
				doc.status = "claimed"
			elif doc.place_type == "Out-Country":
				if doc.supervisor != hr_approver[0]:
					frappe.throw("Only {0} can approve your Out Country Travel Claims".format(hr_approver[1]))
				doc.status = "Claimed"

		elif workflow_state == "Verified By Supervisor".lower():
			if doc.supervisor != frappe.session.user:
				frappe.throw("Only {0} can submit the Travel Authorization".format(doc.supervisor))
			officiating = get_officiating_employee(final_approver[3])
			if officiating:
				officiating = frappe.db.get_value("Employee", officiating[0].officiate, ["user_id","employee_name","designation","name"])
			vars(doc)[document_approver[0]] = officiating[0] if officiating else final_approver[0]
			vars(doc)[document_approver[1]] = officiating[1] if officiating else final_approver[1]
		
		elif workflow_state in ['Rejected', 'Rejected By Supervisor']:
			if workflow_state == "Rejected".lower():
				doc.status = "Rejected"
			vars(doc)[document_approver[0]] = reports_to[0]
	
	else:
		pass