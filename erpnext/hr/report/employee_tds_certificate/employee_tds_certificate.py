# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, formatdate, cstr

def execute(filters=None):
	validate_filters(filters);
	columns = get_columns();
	queries = construct_query(filters);
	data = get_data(queries, filters);

	return columns, data, filters

def get_data(query, filters=None):
	data = []
	datas = frappe.db.sql(query, as_dict=True);
	t_basic = t_allowance = t_gross = t_income = t_nppf = t_gis = t_taxable = t_tds = t_health = 0
	for d in datas:
		allowance = round(flt(d.gross_pay) - flt(d.basic_pay) - (flt(d.comm_all) / 2), 2)
		taxable = flt(d.gross_pay) - flt(d.nppf) - flt(d.gis)
		row = [get_month(d.month), "Salary", d.basic_pay, allowance, d.gross_pay, d.gross_pay, d.nppf,d.gis, taxable, d.tds, d.health, d.receipt_number, d.receipt_date]
		t_basic += flt(d.basic_pay)
		t_allowance += flt(allowance)
		t_gross += flt(d.gross_pay)
		t_nppf += flt(d.nppf)
		t_gis += flt(d.gis)
		t_taxable += flt(taxable)
		t_tds += flt(d.tds)
		t_health += flt(d.health)
		data.append(row);

	#Leave Encashment 
	if filters.employee:
		encash_data = frappe.db.sql("select a.application_date as date, a.encashment_amount, a.tax_amount, r.receipt_number, r.receipt_date from `tabLeave Encashment` a, `tabRRCO Receipt Entries` r where a.name = r.purchase_invoice and a.employee = %s and a.docstatus = 1 and a.application_date between \'" + filters.fiscal_year + "-01-01\' and \'" + filters.fiscal_year + "-12-31\'", filters.employee, as_dict=True) 
		if encash_data:
			for a in encash_data:
				row = [get_month(str(a.date)[5:7]), "Leave Encashment", a.encashment_amount, "", a.encashment_amount, a.encashment_amount, "","", a.encashment_amount, a.tax_amount, "", a.receipt_number, a.receipt_date]
				data.append(row)
				t_basic += flt(a.encashment_amount)
				t_gross += flt(a.encashment_amount)
				t_taxable += flt(a.encashment_amount)
				t_tds += flt(a.tax_amount)

	row = ["Total", "", t_basic, t_allowance, t_gross, t_gross, t_nppf, t_gis, t_taxable, t_tds, t_health, "", ""]
	data.append(row)
	return data

def construct_query(filters=None):
	query = """select a.month, a.gross_pay,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Basic Pay' and b.parent = a.name) as basic_pay,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Salary Tax' and b.parent = a.name) as tds ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'PF' and b.parent = a.name) as nppf ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Group Insurance Scheme' and b.parent = a.name) as gis ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Communication Allowance' and b.parent = a.name) as comm_all ,
	(select b.amount from `tabSalary Detail` b where salary_component = 'Health Contribution' and b.parent = a.name) as health,
	r.receipt_number, r.receipt_date
	 from `tabSalary Slip` a, `tabRRCO Receipt Entries` r
	 where a.fiscal_year = r.fiscal_year and a.month = r.month and a.docstatus = 1 and a.fiscal_year = """ + str(filters.fiscal_year)

	if filters.employee:
		query = query + " AND a.employee = \'" + str(filters.employee) + "\'";

	query+=";";
	
	return query;

def validate_filters(filters):

	if not filters.fiscal_year:
		frappe.throw(_("Fiscal Year {0} is required").format(filters.fiscal_year))

	start, end = frappe.db.get_value("Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"])
	filters.year_start = start
	filters.year_end = end

def get_columns():
	return [
		{
		  "fieldname": "month",
		  "label": "Month",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "type",
		  "label": "Income Type",
		  "fieldtype": "Data",
		  "width": 100
		},
		{
		  "fieldname": "basic",
		  "label": "Basic Salary",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "others",
		  "label": "Other Allowances",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "gross",
		  "label": "Gross Salary",
		  "fieldtype": "Currency",
		  "width": 150
		},
		{
		  "fieldname": "total",
		  "label": "Total Income",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "pf",
		  "label": "NPPF",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "gis",
		  "label": "GIS",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "taxable",
		  "label": "Taxable Income",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "tds",
		  "label": "TDS / PIT",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "health",
		  "label": "Health",
		  "fieldtype": "Currency",
		  "width": 120
		},
		{
		  "fieldname": "receipt_number",
		  "label": "RRCO Receipt No.",
		  "fieldtype": "Data",
		  "width": 150
		},
		{
		  "fieldname": "receipt_date",
		  "label": "RRCO Rt. Date",
		  "fieldtype": "Date",
		  "width": 100
		},
	]

def get_month(month):
	if month == "01":
		return "January"
	elif month == "02":
		return "February"
	elif month == "03":
		return "March"
	elif month == "04":
		return "April"
	elif month == "05":
		return "May"
	elif month == "06":
		return "June"
	elif month == "07":
		return "July"
	elif month == "08":
		return "August"
	elif month == "09":
		return "September"
	elif month == "10":
		return "October"
	elif month == "11":
		return "November"
	elif month == "12":
		return "December"
	else:
		return "None"
