# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.custom_utils import prepare_gl, check_future_date

class HSDPayment(Document):
	def validate(self):
		check_future_date(self.posting_date)
		self.validate_allocated_amount()

	def validate_allocated_amount(self):
		if not self.amount > 0:
			frappe.throw("Amount should be greater than 0")	
		total = flt(self.amount)
		for d in self.items:
			allocated = 0
			if total > 0 and total >= d.payable_amount:
				allocated = d.payable_amount
			elif total > 0 and total < d.payable_amount:
				allocated = total
			else:
				allocated = 0
		
			d.allocated_amount = allocated
			d.balance_amount = d.payable_amount - allocated
			total-=allocated

	def on_submit(self):
		self.adjust_outstanding()
		self.update_general_ledger()

	def on_cancel(self):
		self.adjust_outstanding(cancel=True)
		self.update_general_ledger()
	
	def adjust_outstanding(self, cancel=False):
		for a in self.items:
			doc = frappe.get_doc("POL", a.pol)
			if doc:
				if doc.docstatus != 1:
					frappe.throw("<b>"+ str(doc.name) +"</b> is not a submitted Issue POL Transaction")
				if not cancel:
					doc.db_set("paid_amount", a.allocated_amount)
					doc.db_set("outstanding_amount", a.balance_amount)	
				else:
					doc.db_set("paid_amount", doc.total_amount - doc.outstanding_amount)
					doc.db_set("outstanding_amount", doc.outstanding_amount + a.allocated_amount)	

	def update_general_ledger(self):
		gl_entries = []
		
		creditor_account = frappe.db.get_value("Company", self.company, "default_payable_account")
		if not creditor_account:
			frappe.throw("Set Default Payable Account in Company")

		gl_entries.append(
			prepare_gl(self, {"account": self.bank_account,
					 "credit": flt(self.amount),
					 "credit_in_account_currency": flt(self.amount),
					 "cost_center": self.cost_center,
					})
			)

		gl_entries.append(
			prepare_gl(self, {"account": creditor_account,
					 "debit": flt(self.amount),
					 "debit_in_account_currency": flt(self.amount),
					 "cost_center": self.cost_center,
					 "party_type": "Supplier",
					 "party": self.supplier,
					})
			)

		from erpnext.accounts.general_ledger import make_gl_entries
		make_gl_entries(gl_entries, cancel=(self.docstatus == 2), update_outstanding="No", merge_entries=False)

	def get_invoices(self):
		if not self.fuelbook:
			frappe.throw("Select a Fuelbook to Proceed")
		query = "select name as pol, pol_type as pol_item_code, outstanding_amount as payable_amount, item_name from tabPOL where docstatus = 1 and outstanding_amount > 0 and fuelbook = %s order by posting_date, posting_time"
		entries = frappe.db.sql(query, self.fuelbook, as_dict=True)
		self.set('items', [])

		total_amount = 0
		for d in entries:
			total_amount+=flt(d.payable_amount)
			d.allocated_amount = d.payable_amount
			d.balance_amount = 0
			row = self.append('items', {})
			row.update(d)
		self.amount = total_amount
		self.actual_amount = total_amount
