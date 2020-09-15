# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import get_first_day, get_last_day, add_days, add_years
from frappe.utils import cint, flt, nowdate, money_in_words
from frappe.utils import cint, flt, nowdate, getdate, date_diff, nowdate


class TenantInformation(Document):
	def validate(self):
		if self.building_category != "Pilot Housing":
			self.rent_amount = round(flt(self.floor_area) * flt(self.rate_per_sq_ft))

		self.validate_allocation()
		#if not self.rental_charges and self.building_category != "Pilot Housing":
		#	self.calculate_rent_charges()

		if self.building_category == "Pilot Housing":
			self.cal_monthly_installment_for_pilot_housing()

		if not self.rental_charges and self.building_category == "Pilot Housing":
			self.update_rental_charges()

		if not self.structure_no:
			if not self.location_id:
				self.location_id = frappe.db.get_value("Locations",self.location, "location_id")

			if self.location_id and self.block_no:
				self.structure_no = self.location_id + "-" + self.block_no
			else:
				frappe.msgprint("Structure No. not able to assign as Locaton Id and Block No are missing")
		if not self.percent_of_increment:
			percentage = frappe.db.get_single_value("Rental Setting", "percent_of_increment")
                	self.percent_of_increment = percentage
		if not self.no_of_year_for_increment:	                
			increment_year = cint(frappe.db.get_single_value("Rental Setting", "no_of_year_for_increment"))
                	self.no_of_year_for_increment = increment_year

	def before_rename(self, old, new, merge=False):
		pass

	def after_rename(self, old_cid, new_cid, merge=False):
		if frappe.db.exists("Tenant Information", {"cid": new_cid}):
			frappe.throw("Rename not allowed as CID : {0} is already exist".format(new_cid))
		else:
			frappe.db.sql("update `tabTenant Information` set cid = '{0}' where name = '{0}'".format(new_cid))
			frappe.msgprint("Rename successfully done")
	
	def cal_monthly_installment_for_pilot_housing(self):
		if self.pilot_account_details:
			monthly_installment_amount = 0.0
			for a in self.pilot_account_details:
				monthly_installment_amount += flt(a.amount)

			self.original_monthly_instalment = monthly_installment_amount
	
	def validate_allocation(self):
		if self.status != "Surrendered":
			cid = frappe.db.get_value("Tenant Information", {"location":self.location, "building_category":self.building_category, "block_no":self.block_no, "flat_no":self.flat_no, "docstatus":1, "status":"Allocated"}, "cid")
			if cid:
				frappe.throw("The Flat is already rented to a Tenant with CID No: {0}".format(cid))
			else:
				if frappe.db.exists("Tenant Information", {"location":self.location, "building_category":self.building_category, "block_no":self.block_no, "flat_no":self.flat_no, "docstatus": 1, "status":"Surrendered"}):
					surrendered_date = frappe.db.get_value("Tenant Information", {"location":self.location, "building_category":self.building_category, "block_no":self.block_no, "flat_no":self.flat_no, "docstatus": 1, "status":"Surrendered"}, "surrendered_date")
					if surrendered_date and getdate(self.allocated_date) < getdate(surrendered_date):
						frappe.throw("Allocation Date {0} cannot be before surrendered date {1}".format(self.allocated_date, surrendered_date))

	def on_submit(self):
		self.create_customer()
		if not self.customer_code:
			frappe.throw("Customer ID is missing. You cannot submit without Customer ID.")

		if not self.rental_charges and self.building_category != "Pilot Housing":
			self.calculate_rent_charges()
				
	
	def update_rental_charges(self):
		rent_obj = self.append("rental_charges", {
					"from_date": self.from_date,
					"to_date": self.to_date,
					"increment": 0.0,
					"rental_amount": self.original_monthly_instalment
				})
	
	def calculate_rent_charges(self):
		if self.building_category == "Pilot Housing":
			rent_obj = self.append("rental_charges", {
							"from_date": self.from_date,
							"to_date": self.to_date,
							"increment": 0.00,
							"rental_amount": round(self.original_monthly_instalment)
						})
			rent_obj.save()

		else:
			percentage = frappe.db.get_single_value("Rental Setting", "percent_of_increment")
			increment_year = cint(frappe.db.get_single_value("Rental Setting", "no_of_year_for_increment"))
			self.percent_of_increment = percentage
			self.no_of_year_for_increment = increment_year
			increment = 0.00
			actual_rent = 0.00

			start_date = get_first_day(self.allocated_date)
			end_date = add_years(get_last_day(add_days(start_date, -10)), increment_year)
			if self.percent_of_increment and self.no_of_year_for_increment:
				for i in range(0, 10, increment_year):
					if i > 1:
						start_date = add_years(start_date, increment_year)
						end_date = add_years(end_date, increment_year)
						increment = flt(actual_rent) * flt(flt(percentage)/100) if actual_rent > 0 else flt(self.rent_amount) * flt(flt(percentage)/100)
						actual_rent = flt(actual_rent) + flt(increment) if actual_rent > 0 else flt(self.rent_amount) + flt(increment)
					actual_rent = actual_rent if actual_rent > 0 else self.rent_amount		
					#frappe.msgprint("{0} start: {1} and  end_date: {2} increment {3} and rent {4}".format(i, start_date, end_date, increment, actual_rent))
					rent_obj = self.append("rental_charges", {
								"from_date": start_date,
								"to_date": end_date,
								"increment": increment,
								"rental_amount": round(actual_rent)
							})

					rent_obj.save()
			else:
				frappe.throw("No increment percent and year of increment received from settings ")

	def create_customer(self):
		#Validate Creation of Duplicate Customer in Customer Master
		if frappe.db.exists("Customer", {"customer_id":self.cid, "customer_group": "Rental"}):
			cus = frappe.get_doc("Customer", {"customer_id":self.cid, "customer_group": "Rental"})
			existing_customer_code = frappe.db.get_value("Customer", {"customer_id":self.cid, "customer_group": "Rental"}, "customer_code")
			if existing_customer_code:
				self.customer_code = existing_customer_code
			else:
				last_customer_code = frappe.db.sql("select customer_code from tabCustomer where customer_group='Rental' order by customer_code desc limit 1;");
				if last_customer_code:
					customer_code = str(int(last_customer_code[0][0]) + 1)
				else:
					customer_code = frappe.db.get_value("Customer Group", "Rental", "customer_code_base")
					if not customer_code:
						frappe.throw("Setup Customer Code Base in Rental Customer Group")
				self.db_set("customer_code", customer_code)
				cus.customer_code = customer_code

			cus.mobile_no = self.mobile_no
			cus.location = self.location
			cus.dzongkhag = self.dzongkhag
			cus.save()

		else:
			last_customer_code = frappe.db.sql("select customer_code from tabCustomer where customer_group='Rental' order by customer_code desc limit 1;");
			if last_customer_code:
				customer_code = str(int(last_customer_code[0][0]) + 1)
			else:
				customer_code = frappe.db.get_value("Customer Group", "Rental", "customer_code_base")
				if not customer_code:
					frappe.throw("Setup Customer Code Base in Rental Customer Group")
			self.db_set("customer_code", customer_code)

			cus_name = self.tenant_name + "-" + customer_code

			cus = frappe.new_doc("Customer")
			cus.customer_code = customer_code
			cus.name = customer_code
			cus.customer_name = cus_name
			cus.customer_group = "Rental"
			cus.customer_id = self.cid
			cus.territory = "Bhutan"
			cus.mobile_no = self.mobile_no
			cus.location = self.location
			cus.dzongkhag = self.dzongkhag
			cus.cost_center = "Real Estate Management - NHDCL"
			cus.branch = self.branch
			cus.insert()
		

@frappe.whitelist()
def get_distinct_structure_no():
	data = []
	for a in frappe.db.sql("select distinct(t.structure_no) as structure_no from `tabTenant Information` t where t.structure_no is not NULL and docstatus =1 and not exists (select 1 from `tabAsset` a where a.structure_no= t.structure_no and docstatus = 1)", as_dict=1):
		data.append(a.structure_no)

	return data