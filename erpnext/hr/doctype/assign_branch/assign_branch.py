# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AssignBranch(Document):
	def validate(self):
		self.check_duplicate()

	def on_update(self):
		self.assign_branch()

	def check_duplicate(self):		
		for a in self.items:
			for b in self.items:
				if a.branch == b.branch and a.idx != b.idx:
					frappe.throw("Duplicate Entries in row " + str(a.idx) + " and " + str(b.idx))

	def assign_branch(self):
		#Clear user branch permissions 
		user_perms = frappe.defaults.get_user_permissions(self.user)
		for doc, names in user_perms.items():
			if doc == 'Branch':
				for a in names:
					frappe.permissions.remove_user_permission(doc, a, self.user)
			
		#Add the branch permissions back as per assigned branches
		frappe.permissions.add_user_permission("Branch", self.current_branch, self.user)
		for a in self.items:
			frappe.permissions.add_user_permission('Branch', a.branch, self.user)

		frappe.msgprint("Branch Assigned")
