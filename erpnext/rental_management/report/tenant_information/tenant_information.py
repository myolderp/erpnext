# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_first_day, get_last_day


def execute(filters=None):
	columns  = get_columns()
	data = get_data(filters)
	return columns, data


def get_data(filters):
        cond = get_conditions(filters)
	rent_amount_date = filters.fiscal_year + "-" + filters.month + "-" + "01"
	month_start = get_first_day(rent_amount_date)
	month_end = get_last_day(rent_amount_date)
	# frappe.msgprint(month_start, month_end)
	if filters.building_category == 'Pilot Housing':
			query = """select ti.branch, ti.tenant_name, ti.cid, ti.customer_code, ti.dzongkhag, ti.location,
                ti.town_category, ti.building_classification, ti.building_category, ti.block_no,
                ti.flat_no, ti.structure_no, ti.ministry_agency, ti.department, ti.designation, ti.employee_id, ti.grade, ti.mobile_no, 
                ti.dob, ti.date_of_appointment, ti.pf_account_no, ti.floor_area, 
                ti.rate_per_sq_ft, trc.rental_amount, ti.security_deposit, ti.receipt_no, ti.receipt_date, ti.house_no, ti.area, ti.repayment_period, 
                ti.original_monthly_instalment, ti.initial_allotment_date, ti.allocated_date, ti.status, ti.surrendered_date
                from `tabTenant Information` ti, `tabTenant Rental Charges` trc where case when ti.status = \'Allocated\' then ti.allocated_date <= \'{0}\' when ti.status = \'Surrendered\' then ti.surrendered_date >= \'{1}\' end and trc.parent = ti.name and ti.docstatus = 1 {2}""".format(month_end, month_start, cond)
	else:
			query = """select ti.branch, ti.tenant_name, ti.cid, ti.customer_code, ti.dzongkhag, ti.location,
            ti.town_category, ti.building_classification, ti.building_category, ti.block_no,
            ti.flat_no, ti.structure_no, ti.ministry_agency, ti.department, ti.designation, ti.employee_id, ti.grade, ti.mobile_no, 
            ti.dob, ti.date_of_appointment, ti.pf_account_no, ti.floor_area, 
            ti.rate_per_sq_ft, trc.rental_amount, ti.security_deposit, ti.receipt_no, ti.receipt_date, ti.house_no, ti.area, ti.repayment_period, 
            ti.original_monthly_instalment, ti.initial_allotment_date, ti.allocated_date, ti.status, ti.surrendered_date
            from `tabTenant Information` ti, `tabTenant Rental Charges` trc where case when ti.status = \'Allocated\' then ti.allocated_date <= \'{0}\' when ti.status = \'Surrendered\' then ti.surrendered_date >= \'{1}\' end and trc.parent = ti.name and ti.docstatus = 1 {2}""".format(month_end, month_start, cond)

			query += " and \'{0}\' between trc.from_date and trc.to_date".format(rent_amount_date)

	if filters.rental_status:
			query += " and ti.status = '{0}'".format(filters.rental_status)
	
	if filters.block_no:
			query += " and ti.block_no = '{0}'".format(filters.block_no)
        return frappe.db.sql(query)

def get_conditions(filters):
        condition = ""
        if filters.dzongkhag:
                condition += " and ti.dzongkhag = '{0}'".format(filters.dzongkhag)
        if filters.location:
                condition += " and ti.location = '{0}'".format(filters.location)
        if filters.building_category:
                condition += " and ti.building_category = '{0}'".format(filters.building_category)
        return condition


def get_columns():
	return[
		("Branch") + ":Link/Branch:120",
		("Tenant Name") + ":Data:120",
		("CID No.") + ":Link/Tenant Information:100",
		("Customer Code") + ":Data:80",
		("Tenant Dzongkhag") + ":Data:120",
		("location") + ":Data:120",
		("Town Category") + ":Data:120",
		("Building Classification") + ":Data:120",
		("Building Category") + ":Data:120",
        	("Block No") + ":Data:80",
		("Flat No") + ":Data:80",
		("Structure No") + ":Data:130",
		("Ministry/Agency") + ":Data:120",
		("Department") + ":Data:120",
		("Designation") + ":Data:120",
		("Employee ID") + ":Data:120",
		("Grade") + ":Data:120",
        	("Mobile No") + ":Data:120",
		("Date of Birth") + ":Data:120",
		("Date of Appointment In Service") + ":Data:120",
		("Provident Fund A/C No.") + ":Data:120",
		("Floot Area (Sqft)") + ":Data:120",
		("Rate per Sqft") + ":Data:120",
		("Rent Amount") + ":Currency:120",
		("Security Deposit") + ":Currency:120",
		("SD Receipt No.") + ":Data:120",
		("SD Receipt Date") + ":Date:100",
        	("House No") + ":Data:120",
		("Land area (Sq.m)") + ":Data:100",
		("Repayment Period") + ":Data:100",
		("Original Monthly Installment") + ":Data:120",
		("Initial Allocated Date") + ":Data:120",
		("Allocated Date") + ":Data:120",
		("Rental Status") + ":Data:100",
		("Surrendered Date") + ":Data:100"
		]	