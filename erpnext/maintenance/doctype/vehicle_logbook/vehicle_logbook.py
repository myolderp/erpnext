# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, add_days
from erpnext.custom_utils import check_uncancelled_linked_doc, check_future_date

class VehicleLogbook(Document):
	def validate(self):
		check_future_date(self.to_date)
		self.check_dates()
		self.check_double_vl()
		self.check_hire_form()
		##self.check_hire_rate()
		self.check_duplicate()
		self.update_consumed()
		self.calculate_totals()
		self.update_operator()
		self.check_consumed()	

	def check_consumed(self):
		if self.include_hour or self.include_km:
			if flt(self.consumption) <= 0:
				frappe.throw("Total consumption cannot be zero or less")

	def check_hire_rate(self):
                based_on = frappe.db.get_single_value("Mechanical Settings", "hire_rate_based_on")
                if not based_on:
                        frappe.throw("Set the <b>Hire Rate Based On</b> in <b>Mechanical Settings</b>")

                e = frappe.get_doc("Equipment", self.equipment)

                db_query = "select a.rate_fuel, a.rate_wofuel, a.idle_rate, a.yard_hours, a.yard_distance from `tabHire Charge Item` a, `tabHire Charge Parameter` b where a.parent = b.name and b.equipment_type = '{0}' and b.equipment_model = '{1}' and '{2}' between a.from_date and ifnull(a.to_date, now()) and '{3}' between a.from_date and ifnull(a.to_date, now()) LIMIT 1"
                data = frappe.db.sql(db_query.format(e.equipment_type, e.equipment_model, self.from_date, self.to_date), as_dict=True)
                if not data:
                        frappe.throw("There is either no Hire Charge defined or your logbook period overlaps with the Hire Charge period.")
                if based_on == "Hire Charge Parameter" and not self.tender_hire_rate:
                        if self.rate_type == "With Fuel":
                                self.work_rate = data[0].rate_fuel
                                self.idle_rate = data[0].idle_rate
                        if self.rate_type == "Without Fuel":
                                self.work_rate = data[0].rate_wofuel
                                self.idle_rate = data[0].idle_rate
                self.ys_km = data[0].yard_distance
                self.ys_hours = data[0].yard_hours

	def on_update(self):
		self.calculate_balance()

	def on_submit(self):
		self.check_double_vl()
		self.update_consumed()
		self.calculate_totals()
		self.check_consumption()
		self.update_hire()
		self.post_equipment_status_entry()
		#self.check_tank_capacity()
	
	def on_cancel(self):
		docs = check_uncancelled_linked_doc(self.doctype, self.name)
                if docs != 1:
                        frappe.throw("There is an uncancelled <b>" + str(docs[0]) + "("+ str(docs[1]) +")</b> linked with this document")
		frappe.db.sql("delete from `tabEquipment Status Entry` where ehf_name = \'"+str(self.name)+"\'")

	def check_dates(self):
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw("From Date cannot be smaller than To Date")

		if getdate(self.from_date).month != getdate(self.to_date).month:
                        frappe.throw("From Date and To Date should be in the same month")

	def check_hire_form(self):
		if self.ehf_name:
			docstatus = frappe.db.get_value("Equipment Hiring Form", self.ehf_name, "docstatus")
			if docstatus != 1:
				frappe.throw("Cannot create Vehicle Logbook without submitting Hire Form")
		try:
			name = frappe.db.sql("select name from `tabHiring Approval Details` where parent = %s and equipment = %s", (self.ehf_name, self.equipment))[0]
		except:
			frappe.throw("Make sure the equipment you selected is in the corresponding hire form")	

	def update_operator(self):
		self.equipment_operator = frappe.db.get_value("Equipment", self.equipment, "current_operator")

	def check_duplicate(self):		
		for a in self.vlogs:
			for b in self.vlogs:
				if a.date == b.date and a.idx != b.idx:
					frappe.throw("Duplicate Dates in Vehicle Logs in row " + str(a.idx) + " and " + str(b.idx))

	def update_consumed(self):
		pol_type = frappe.db.get_value("Equipment", self.equipment, "hsd_type")
		closing = frappe.db.sql("select closing_balance, to_date from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by to_date desc limit 1", (self.equipment, self.from_date), as_dict=True)

		if closing:
			qty = frappe.db.sql("select sum(qty) as qty from `tabConsumed POL` where equipment = %s and date between %s and %s and docstatus = 1 and pol_type = %s", (self.equipment, add_days(closing[0].to_date, 1), self.to_date, pol_type), as_dict=True)
		else:
			qty = frappe.db.sql("select sum(qty) as qty from `tabConsumed POL` where equipment = %s and date <= %s and docstatus = 1 and pol_type = %s", (self.equipment, self.to_date, pol_type), as_dict=True)
		if qty:
			self.hsd_received = qty[0].qty

	def calculate_totals(self):
		if self.vlogs:
			total_w = total_i = 0
			for a in self.vlogs:
				total_w += flt(a.work_time)
				total_i += flt(a.idle_time)
			self.total_work_time = total_w
			self.total_idle_time = total_i

		if self.include_km:
			self.consumption_km = flt(self.ys_km) * flt(self.distance_km)

		if self.include_hour:
			self.consumption_hours = flt(self.ys_hours) * flt(self.total_work_time)
		
		self.consumption = flt(self.other_consumption) + flt(self.consumption_hours) + flt(self.consumption_km)
		self.closing_balance = flt(self.hsd_received) + flt(self.opening_balance) - flt(self.consumption)

	def update_hire(self):
		if self.ehf_name:
			doc = frappe.get_doc("Equipment Hiring Form", self.ehf_name)
			doc.db_set("hiring_status", 1)
		e = frappe.get_doc("Equipment", self.equipment)

		if self.final_km:
			self.check_repair(cint(e.current_km_reading), cint(self.final_km))
			e.db_set("current_km_reading", flt(self.final_km))

		if self.final_hour:
			self.check_repair(cint(e.current_hr_reading), cint(self.final_hour))
			e.db_set("current_hr_reading", flt(self.final_hour))

	def post_equipment_status_entry(self):
		doc = frappe.new_doc("Equipment Status Entry")
		doc.flags.ignore_permissions = 1 
		doc.equipment = self.equipment
		doc.reason = "Hire"
		doc.ehf_name = self.name
		doc.from_date = self.from_date
		doc.to_date = self.to_date
		doc.hours = self.total_work_time
		doc.to_time = self.to_time
		doc.from_time = self.from_time
		doc.place = frappe.db.sql("select place from `tabHiring Approval Details` where parent = %s and equipment = %s", (self.ehf_name, self.equipment))[0]
		doc.submit()

	def calculate_balance(self):
		self.db_set("closing_balance", flt(self.opening_balance) + flt(self.hsd_received) - flt(self.consumption))

	def check_repair(self, start, end):
		et, em, branch = frappe.db.get_value("Equipment", self.equipment, ["equipment_type", "equipment_model", "branch"])
		interval = frappe.db.get_value("Hire Charge Parameter", {"equipment_type": et, "equipment_model": em}, "interval")
		if interval:
			for a in xrange(start, end):
				if (flt(a) % flt(interval)) == 0:
					mails = frappe.db.sql("select email from `tabRegular Maintenance Item` where parent = %s", branch, as_dict=True)
					for b in mails:
						subject = "Regular Maintenance for " + str(self.equipment)
						message = "It is time to do regular maintenance for equipment " + str(self.equipment) + " since it passed the hour/km reading of " + str(a) 
						if b.email:
							try:
								frappe.sendmail(recipients=b.email, sender=None, subject=subject, message=message)
							except:
								pass
					break

	def check_tank_capacity(self):
		em = frappe.db.get_value("Equipment", self.equipment, "equipment_model")
		tank = frappe.db.get_value("Equipment Model", em, "tank_capacity") 
		if tank:
			if flt(tank) < flt(self.closing_balance):
				frappe.msgprint("Closing balance cannot be greater than the tank capacity (" + str(tank) + ")")

	def check_double_vl(self):
		result = frappe.db.sql("select ehf_name from `tabVehicle Logbook` where equipment = \'" + str(self.equipment) + "\' and docstatus in (1, 0) and (\'" + str(self.from_date) + "\' between from_date and to_date OR \'" + str(self.to_date) + "\' between from_date and to_date) and name != \'" + str(self.name) + "\'", as_dict=True)
		if result:
			if self.from_time and self.to_time:
				res = frappe.db.sql("select name from `tabVehicle Logbook` where docstatus in (1, 0) and equipment = %s and ehf_name = %s and (%s > from_time or %s < to_time)", (str(self.equipment), str(result[0].ehf_name), str(self.from_time), str(self.to_time)))
				if res:
					frappe.throw("The logbook for the same equipment, date, and time has been created at " + str(result[0].ehf_name))
			else:
				frappe.throw("The logbook for the same equipment, date, and time has been created at " + str(result[0].ehf_name))

	def check_consumption(self):
		customer = frappe.db.get_value("Equipment Hiring Form", self.ehf_name, "private")
		if customer == "CDCL" and not self.consumption_km and not self.consumption_hours and not self.consumption:
			frappe.throw("Consumption is mandatory for Internal Use")
		if customer != "CDCL" and (self.consumption_km > 0 or self.consumption_hours > 0) and self.rate_type == "Without Fuel":
			frappe.throw("Should not have consumption when on dry hire to outside customers")

@frappe.whitelist()
def get_opening(equipment, from_date, to_date, pol_type):
	if not pol_type:
		frappe.throw("Set HSD type in Equipment")

	closing = frappe.db.sql("select name, closing_balance, to_date, final_km, final_hour from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by to_date desc, to_time desc limit 1", (equipment, from_date), as_dict=True)

	if closing:
		qty = frappe.db.sql("select sum(qty) as qty from `tabConsumed POL` where equipment = %s and date between %s and %s and docstatus = 1 and pol_type = %s", (equipment, add_days(closing[0].to_date, 1), to_date, pol_type), as_dict=True)
	else:
		qty = frappe.db.sql("select sum(qty) as qty from `tabConsumed POL` where equipment = %s and date <= %s and docstatus = 1 and pol_type = %s", (equipment, to_date, pol_type), as_dict=True)

	c_km = frappe.db.sql("select final_km from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by to_date desc limit 1", (equipment, from_date), as_dict=True)

	c_hr = frappe.db.sql("select final_hour from `tabVehicle Logbook` where docstatus = 1 and equipment = %s and to_date <= %s order by to_date desc limit 1", (equipment, from_date), as_dict=True)
	result = []
	if closing:
		result.append(closing[0].closing_balance)
		result.append(closing[0].final_km)
		result.append(closing[0].final_hour)
	else:
		result.append(0)
		result.append(0)
		result.append(0)

	if qty:
		result.append(qty[0].qty)
	else:
		result.append(0)

	'''if c_km:
		result.append(c_km[0].final_km)
	else:
		result.append(0)

	if c_hr:
		result.append(c_hr[0].final_hour)
	else:
		result.append(0)'''

	return result

		
