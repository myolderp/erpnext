# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class PBVA(Document):
	def validate(self):
		pass

	def on_submit(self):
		cc_amount = {}
		for a in self.items:
			cc = frappe.db.get_value("Division", frappe.db.get_value("Employee", a.employee, "division"), "cost_center")
			if cc_amount.has_key(cc):
				cc_amount[cc] = cc_amount[cc] + a.amount
			else:
				cc_amount[cc] = a.amount;
		
		self.post_journal_entry(cc_amount)

	def post_journal_entry(self, cc_amount):
		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions = 1 
		je.title = "PBVA (" + self.name + ")"
		je.voucher_type = 'Bank Entry'
		je.naming_series = 'Bank Payment Voucher'
		je.remark = 'PBVA payment against : ' + self.name;
		je.posting_date = self.posting_date

		for key in cc_amount.keys():
			je.append("accounts", {
					"account": "Performance Based Variable Pay - SMCL",
					"reference_type": "PBVA",
					"reference_name": self.name,
					"cost_center": key,
					"debit_in_account_currency": flt(cc_amount[key]),
					"debit": flt(cc_amount[key]),
				})
		
		je.append("accounts", {
				"account": "Bank of Bhutan Ltd - 100891887 - SMCL",
				"reference_type": "PBVA",
				"reference_name": self.name,
				"cost_center": "Corporate Head Office - SMCL",
				"credit_in_account_currency": flt(self.total_amount) - flt(self.tax_amount),
				"credit": flt(self.total_amount) - flt(self.tax_amount),
			})
		
		je.append("accounts", {
				"account": "Salary Tax - SMCL",
				"reference_type": "PBVA",
				"reference_name": self.name,
				"cost_center": "Corporate Head Office - SMCL",
				"credit_in_account_currency": flt(self.tax_amount),
				"credit": flt(self.tax_amount),
			})

		je.insert()

		self.db_set("journal_entry", je.name)

	def on_cancel(self):
		jv = frappe.db.sql("select name, docstatus from `tabJournal Entry` where name = %s and docstatus = 1", self.journal_entry)
		if jv:
			frappe.throw("Can not cancel PBVA without canceling the corresponding journal entry " + str(self.journal_entry))
		else:
			self.db_set("journal_entry", "")


@frappe.whitelist()
def get_pbva_details(branch=None):
	query = "select b.employee, b.employee_name, b.branch, a.amount from `tabSalary Detail` a, `tabSalary Structure` b where a.parent = b.name and a.salary_component = 'Basic Pay' and b.is_active = 'Yes' and b.eligible_for_pbva = 1 "
	if branch:
		query += " and b.branch = \'" + str(branch) + "\'";
	query += " order by b.branch"
	return frappe.db.sql(query, as_dict=True)

@frappe.whitelist()
def get_pbva_percent(employee):
	group = frappe.db.get_value("Employee", employee, "employee_group")
	if group in ("Chief Executive Officer", "Executive"):
		return "above"
	else:
		return "below"
