# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Equipment(Document):
	def validate(self):
		if self.asset_code:
			doc = frappe.get_doc("Asset", self.asset_code)
			doc.db_set("equipment_number", self.name)

		if not self.equipment_number:
			self.equipment_number = self.name
