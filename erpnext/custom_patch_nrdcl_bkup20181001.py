from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import msgprint
from frappe.utils import flt, cint, now, nowdate, getdate
from frappe.utils.data import date_diff, add_days, get_first_day, get_last_day, add_years
from erpnext.hr.hr_custom_functions import get_month_details, get_company_pf, get_employee_gis, get_salary_tax, update_salary_structure
from datetime import timedelta, date
from erpnext.custom_utils import get_branch_cc, get_branch_warehouse

def migrate_species():
	for a in frappe.db.sql("select name, is_conifer from `tabTimber Species`", as_dict=1):
		if a.is_conifer:
			t = "Conifer" 
		else:
			t = "Broadleaf" 
		frappe.db.sql("update `tabTimber Species` set timber_type = %s where name = %s", (t, a.name))

def delete_users():
	for a in frappe.db.sql("select name from tabUser where btl != 1", as_dict=1):
		doc = frappe.get_doc("User", a.name)
		print a.name
		doc.delete()
		frappe.db.commit()

def update_equipment_history():
        equ = frappe.db.sql("select name from `tabEquipment`", as_dict =1)
        for eq in equ:
                print(eq)
                doc = frappe.get_doc("Equipment", eq.name)
                #doc.business_activity = 'Test BA'
                doc.save()

def move_cc_branch():
	ccs = frappe.db.sql("select name, branch from `tabCost Center` where branch is not null", as_dict=1)
	for cc in ccs:
		print(cc.branch)
		if cc.branch:
			b = frappe.get_doc("Branch", cc.branch)
			b.db_set("cost_center", cc.name)


def update_mech():
        ml = frappe.db.sql("select name from `tabMechanical Payment` where docstatus = 1 and payment_for is null and name = 'MP18090001'", as_dict=1)
        for a in ml:
                doc = frappe.get_doc("Mechanical Payment", a.name)
                print(doc.name)
		frappe.db.sql("update `tabMechanical Payment` set payment_for = %s where name = %s", (doc.ref_doc, doc.name))
                dc = frappe.new_doc("Mechanical Payment Item")
                dc.reference_type = doc.ref_doc
                dc.reference_name = doc.ref_no
                dc.outstanding_amount = doc.receivable_amount
                dc.allocated_amount = doc.receivable_amount
                dc.parent = doc.name
                dc.parenttype = "Mechanical Payment"
                dc.parentfield = "items"
                dc.owner = doc.owner
                dc.creation = doc.creation
                dc.modified_by = doc.modified_by
                dc.modified = doc.modified
                dc.docstatus = doc.docstatus
                dc.submit()
                dc.idx = 1

def adjust_advance_balance():
	advances = frappe.db.sql("select name from `tabHire Charge Invoice`", as_dict=1)
	for a in advances:
		doc = frappe.get_doc("Hire Charge Invoice", a.name)
		total = 0
		for b in doc.advances:
			total = flt(total) + flt(b.balance_advance_amount)
		if total != 0:
			print(str(a.name) + " ==> " + str(total))
			frappe.db.sql("update `tabHire Charge Invoice` set balance_advance_amount = %s where name = %s", (total, a.name))

def hire_balance_advance():
	advs = frappe.db.sql("select parent, name, actual_advance_amount, allocated_amount from `tabHire Invoice Advance`", as_dict=1)
	for a in advs:
		bal = flt(a.actual_advance_amount) - flt(a.allocated_amount)
		print(a.parent)
		frappe.db.sql("update `tabHire Invoice Advance` set balance_advance_amount = %s where name = %s", (bal, a.name))

def update_vl():
	vls = frappe.db.sql("select name, ehf_name from `tabVehicle Logbook`", as_dict=1)
	for a in vls:
		doc = frappe.get_doc("Equipment Hiring Form", a.ehf_name)
		print(doc.name)
		frappe.db.sql("update `tabVehicle Logbook` set customer_type = %s, customer = %s where name = %s", (doc.private, doc.customer, a.name))

def update_hcp():
	hcps = frappe.db.sql("select name from `tabHire Charge Parameter`", as_dict=1)
	for a in hcps:
		doc = frappe.get_doc("Hire Charge Parameter", a.name)
		doc.save()

def update_pol_time():
	pols = frappe.db.sql("select name, reference_name, reference_type from `tabPOL Entry` where reference_name is not null and reference_type is not null", as_dict=1)
	for a in pols:
		if a.reference_type and a.reference_name:
			doc = frappe.get_doc(a.reference_type, a.reference_name)
			print(a.name)
			frappe.db.sql("update `tabPOL Entry` set posting_time = %s where name = %s", (str(doc.posting_time), a.name))

def update_table():
        tables = frappe.db.sql("SELECT table_name FROM information_schema.tables where table_schema='4915427b5860138f'", as_dict=True)
        for a in tables:
                try:    
                        frappe.db.sql("ALTER TABLE `"+str(a.table_name)+"` ADD COLUMN submitted_by varchar(140)")
                        print(a.table_name)
                except: 
                        pass

def adjust_asset_gl():
	#ams = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1 ", as_dict=True)
	ams = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1 and posting_date > '2017-12-31'", as_dict=True)
	cc = 0
	for a in ams:
		doc = frappe.get_doc("Asset Movement", a.name)
		if ((doc.target_cost_center and doc.target_cost_center != doc.current_cost_center) or (doc.target_custodian and doc.current_cost_center != doc.target_custodian_cost_center)):
			cc = cc + 1
			if doc.target_cost_center:
				to_cc = doc.target_cost_center
			else:
				to_cc = doc.target_custodian_cost_center
			do_gl_adjustment(doc, doc.asset, doc.posting_date, doc.name, doc.current_cost_center, to_cc)

	bam = frappe.db.sql("select name from `tabBulk Asset Transfer` where docstatus = 1 and posting_date > '2017-12-31'", as_dict=1)
	for a in bam:
		doc = frappe.get_doc("Bulk Asset Transfer", a.name)
		for b in doc.items:
			if b.cost_center != doc.custodian_cost_center:
				cc = cc + 1
				do_gl_adjustment(doc, str(b.asset_code), doc.posting_date, doc.name, b.cost_center, doc.custodian_cost_center)

	print(cc)

def do_gl_adjustment(self, asset_code, posting_date, name, from_cc, to_cc):
	asset = frappe.get_doc("Asset", asset_code)
	deps = frappe.db.sql("select accumulated_depreciation_amount from `tabDepreciation Schedule` where parent = %s and schedule_date <= %s order by schedule_date desc limit 1", (asset_code, posting_date),  as_dict=1)
	if deps:
		accumulated_dep = deps[0].accumulated_depreciation_amount
	else:
		accumulated_dep = asset.opening_accumulated_depreciation
	
	ic_amount = flt(asset.gross_purchase_amount) - flt(accumulated_dep)

	accumulated_dep_account = frappe.db.sql("select accumulated_depreciation_account from `tabAsset Category Account` where parent = %s", asset.asset_category, as_dict=True)[0].accumulated_depreciation_account
	ic_account = frappe.db.get_single_value("Accounts Settings", "intra_company_account")
	if not ic_account:
		frappe.throw("Setup Intra Company Accounts under Accounts Settings")

	from erpnext.accounts.general_ledger import make_gl_entries
	from erpnext.custom_utils import prepare_gl

	gl_entries = []
	gl_entries.append(
		prepare_gl(self, {
		       "account":  asset.asset_account,
		       "credit": asset.gross_purchase_amount,
		       "credit_in_account_currency": asset.gross_purchase_amount,
		       "against_voucher": asset.name,
		       "against_voucher_type": "Asset",
		       "cost_center": from_cc,
		})
	)
	gl_entries.append(
		prepare_gl(self, {
		       "account":  asset.asset_account,
		       "debit": asset.gross_purchase_amount,
		       "debit_in_account_currency": asset.gross_purchase_amount,
		       "against_voucher": asset.name,
		       "against_voucher_type": "Asset",
		       "cost_center": to_cc,
		})
	)

	if accumulated_dep:
		gl_entries.append(
			prepare_gl(self, {
			       "account": accumulated_dep_account,
			       "debit": accumulated_dep,
			       "debit_in_account_currency": accumulated_dep,
			       "against_voucher": asset.name,
			       "against_voucher_type": "Asset",
			       "cost_center": from_cc,
			})
		)
		gl_entries.append(
			prepare_gl(self, {
			       "account": accumulated_dep_account,
			       "credit": accumulated_dep,
			       "credit_in_account_currency": accumulated_dep,
			       "against_voucher": asset.name,
			       "against_voucher_type": "Asset",
			       "cost_center": to_cc,
			})
		)

	if ic_amount:
		gl_entries.append(
			prepare_gl(self, {
			       "account": ic_account,
			       "debit": ic_amount,
			       "debit_in_account_currency": ic_amount,
			       "against_voucher": asset.name,
			       "against_voucher_type": "Asset",
			       "cost_center": from_cc,
			})
		)
		gl_entries.append(
			prepare_gl(self, {
			       "account": ic_account,
			       "credit": ic_amount,
			       "credit_in_account_currency": ic_amount,
			       "against_voucher": asset.name,
			       "against_voucher_type": "Asset",
			       "cost_center": to_cc,
			})
		)

	print(asset.name)
	make_gl_entries(gl_entries, cancel=0, update_outstanding="No", merge_entries=False)

def branch_access_list():
	bl = frappe.db.sql("select count(1) as count, parent from tabDefaultValue where defkey = 'Branch' group by parent having count > 1", as_dict=True)
	for a in bl:
		ab = frappe.db.sql("select 1 from `tabAssign Branch` where user = %s", a.parent, as_dict=1)
		if not ab:
			print(a)

def get_asset_list():
	li = frappe.db.sql("select a.gross_purchase_amount, a.name, a.asset_account, b.fixed_asset_account from tabAsset a, `tabAsset Category Account` b where a.asset_category = b.parent and a.asset_account != b.fixed_asset_account", as_dict=True)
	for a in li:
		print(a.name + "  :  " + a.asset_account + " ==> " + a.fixed_asset_account + "   ::: " + str(a.gross_purchase_amount))

	"""assets = frappe.db.sql("select a.name, a.asset_category, b.account from tabAsset a, `tabJournal Entry Account` b where b.debit > 0 and a.name = b.reference_name and (b.account not like '%Depreciation%' and b.account not like '%Amortization%')", as_dict=True)
	for a in assets:
		as_cat = frappe.db.sql("select fixed_asset_account from `tabAsset Category Account` where parent = %s", a.asset_category, as_dict=True)
		entry = as_cat[0].fixed_asset_account
		if a.account != entry:
			print(a.name + "  :  " + a.account + " ==> " + entry)
	"""

def move_bulk_asset_movement():
	ams = frappe.db.sql("select name, creation from `tabBulk Asset Transfer`", as_dict=True)
	for a in ams:
		print(a.name + " : " + str(getdate(a.creation)))
		frappe.db.sql("update `tabBulk Asset Transfer` set posting_date = %s, company = %s where name = %s", (str(getdate(a.creation)), "Construction Development Corporation Ltd", a.name))

def move_asset_movement():
	ams = frappe.db.sql("select name, transaction_date, reason from `tabAsset Movement`", as_dict=True)
	for a in ams:
		frappe.db.sql("update `tabAsset Movement` set posting_date = %s, remarks = %s where name = %s", (a.transaction_date, a.reason, a.name))

def adjust_km_consumption():
	vlogs = frappe.db.sql("select name, ys_km, distance_km, consumption_km from `tabVehicle Logbook` where consumption_km = distance_km * ys_km and consumption_km != 0", as_dict=True)
	for a in vlogs:
		#total = flt(a.distance_km) / flt(a.ys_km)
		#frappe.db.sql("update `tabVehicle Logbook` set consumption_km = %s, consumption = %s where name = %s", (total, total, a.name))
		print(a.name)

def logbook_consumption_others():
	logs = frappe.db.sql("select l.name from `tabVehicle Logbook` l, `tabEquipment Hiring Form` e where l.ehf_name = e.name and e.private != 'CDCL' and l.rate_type = 'Without Fuel' and l.consumption > 0 and l.docstatus = 1 and l.from_date > '2018-03-31'", as_dict=True)
	for a in logs:
		print(a.name)

def logbook_cunsumption():
	logs = frappe.db.sql("select l.name, l.branch from `tabVehicle Logbook` l, `tabEquipment Hiring Form` e where l.ehf_name = e.name and e.private = 'CDCL' and l.consumption = 0 and l.docstatus = 1 and l.from_date > '2018-03-31'", as_dict=True)
	#logs = frappe.db.sql("select l.name, l.branch from `tabVehicle Logbook` l, `tabEquipment Hiring Form` e where l.ehf_name = e.name and e.private = 'CDCL' and l.consumption = 0 and l.docstatus = 1 ", as_dict=True)
	both = km = time = none = 0
	for a in logs:
		distance = hours = consump = 0
		log = frappe.get_doc("Vehicle Logbook", a.name)
		if not log.ys_km and not log.ys_hours:
			pass
		if log.total_work_time and log.distance_km:
			#print("Both: " + str(log.name))
			if log.ys_km and log.ys_hours:
				distance = log.distance_km / log.ys_km
				hours = log.total_work_time * log.ys_hours
			elif log.ys_km:
				distance = log.distance_km / log.ys_km
			elif log.ys_hours:
				hours = log.total_work_time * log.ys_hours
			else:
				distance = log.distance_km / log.ys_km
				hours = log.total_work_time * log.ys_hours
		elif log.total_work_time:
			hours = log.total_work_time * log.ys_hours
		elif log.distance_km:
			distance = log.distance_km / log.ys_km
		else:
			distance = log.distance_km / log.ys_km
			hours = log.total_work_time * log.ys_hours
		consump = log.other_consumption + hours + distance
		if distance > 0 and hours > 0:
			tp, mo = frappe.db.get_value("Equipment", log.equipment, ['equipment_type', 'equipment_model'])	
			if tp not in ['Jack Hammer', 'Rock Breaker']:
				print("BOTH: " + a.name + " : " + log.branch)
		elif distance > 0:
			frappe.db.sql("update `tabVehicle Logbook` set include_km = 1, consumption_km = %s, consumption = %s where name = %s", (distance, consump, log.name))
		elif hours > 0:
			frappe.db.sql("update `tabVehicle Logbook` set include_hour = 1, consumption_hours = %s, consumption = %s where name = %s", (hours, consump, log.name))
		else:
			tp, mo = frappe.db.get_value("Equipment", log.equipment, ['equipment_type', 'equipment_model'])	
			if tp not in ['Jack Hammer', 'Rock Breaker']:
				print("NONE: " + a.name + " : " + log.branch)

def check_double_pol():
	pols = frappe.db.sql("select p.name from tabPOL p, `tabJournal Entry` j where p.docstatus = 1 and p.jv is not null and j.docstatus = 1 and p.jv = j.name", as_dict=True)
	for a in pols:
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)

def set_cc_kilikhar():
	gls = frappe.db.sql("select a.advance_cost_center, b.name from `tabSales Invoice Advance` a, `tabGL Entry` b where a.docstatus = 1 and a.parent = b.voucher_no and a.advance_account = b.against", as_dict=True)
	for a in gls:
		frappe.db.sql("update `tabGL Entry` set cost_center = %s where name = %s", (a.advance_cost_center, a.name))
		print(a.name)

def set_operator_name():
	ops = frappe.db.sql("select parent, name, operator, employee_type from `tabEquipment Operator` where operator_name is null", as_dict=True)
	for a in ops:
		if a.employee_type == "Employee":
			name = frappe.db.get_value("Employee", a.operator, "employee_name")
		else:
			name = frappe.db.get_value("Muster Roll Employee", a.operator, "person_name")
		frappe.db.sql("update `tabEquipment Operator` set operator_name = %s where name = %s", (name, a.name))

def link_consumed_committed():
	con = frappe.db.sql("select name, pii_name from `tabConsumed Budget` where docstatus = 1", as_dict=True)
	for a in con:
		if a.pii_name:
			try:
				doc = frappe.get_doc("Purchase Invoice Item", a.pii_name)
				if doc:
					print(doc.po_detail)
					frappe.db.sql("update `tabConsumed Budget` set poi_name = %s where name = %s", (doc.po_detail, a.name))
			except:
				pass

def adjust_pol_journal():
	pols = frappe.db.sql("select name from tabPOL where docstatus = 1 and direct_consumption = 1 and posting_date > '2017-12-31'", as_dict=True)
	for a in pols:
		print(a.name)
		doc = frappe.get_doc("POL", a.name)
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		doc.update_general_ledger(1)

def set_equipment_type():
	pols = frappe.db.sql("select name, equipment from tabPOL", as_dict=True)
	for a in pols:
		print(a.equipment)
		et = frappe.db.get_value("Equipment", a.equipment, "equipment_type")
		frappe.db.sql("update tabPOL set equipment_type = %s where name = %s", (et, a.name))	

def adjust_pol_entry_1():
	pol = frappe.get_doc("POL", "POL180500576")
	frappe.db.sql("delete from `tabPOL Entry` where reference_name = 'POL180500576'")
	pol.make_pol_entry()

def adjust_dc_pol():
	pols = frappe.db.sql("select p.name, p.qty, e.equipment_type, p.posting_date, p.equipment_warehouse from tabPOL p, tabEquipment e, `tabEquipment Type` et where p.equipment = e.name and e.equipment_type = et.name and direct_consumption = 0 and et.is_container = 0 and posting_date > '2018-03-31' and p.docstatus = 1 ", as_dict=True)
	for a in pols:
		if a.name in ['POL180500492', 'POL180500491', 'POL180500490', 'POL180500456']:
			print(str(a.name))
			frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no = %s", a.name)
			frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
			frappe.db.sql("update `tabPOL` set direct_consumption = 1 where name = %s", a.name)
			doc = frappe.get_doc("POL", a.name)
			doc.direct_consumption = 1
			doc.update_stock_ledger()
			doc.make_pol_entry()
			frappe.db.commit()
		else:	
			pass
			"""print(str(a.name))
			frappe.db.sql("delete from `tabStock Ledger Entry` where voucher_no = %s", a.name)
			frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
			frappe.db.sql("update `tabPOL` set direct_consumption = 1 where name = %s", a.name)
			doc = frappe.get_doc("POL", a.name)
			doc.direct_consumption = 1
			doc.update_stock_ledger()
			doc.make_pol_entry()
			frappe.db.commit()"""

def adjust_hsd_outstanding():
	ols = frappe.db.sql("select pol from `tabHSD Payment Item` where parent = 'HSDP1805002'", as_dict=True)
	for a in ols:
		print(a.pol)
		frappe.db.sql("update `tabPOL` set paid_amount = '' where name = %s", a.pol)

def update_asset():
	prs = frappe.db.sql("select name from `tabPurchase Receipt` where docstatus = 1", as_dict=True)
	for a in prs:
		print(a.name)
		doc = frappe.get_doc("Purchase Receipt", a.name)
		doc.delete_asset()
		doc.update_asset()

def make_status_entry():
	vls = frappe.db.sql("select name from `tabJob Card` where docstatus = 1", as_dict=True)
	for a in vls:
		print(str(a.name))
		doc = frappe.get_doc("Job Card", a.name)
		doc.update_reservation()

def make_pol_entry():
	"""pols = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("Issue POL", a.name)
		doc.make_pol_entry()
	frappe.db.commit()"""

	pols = frappe.db.sql("select name from `tabPOL` where docstatus = 1 and pol_type != 'N/A'", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("POL", a.name)
		doc.make_pol_entry() 
	frappe.db.commit()

	"""pols = frappe.db.sql("select name from `tabEquipment POL Transfer` where docstatus = 1", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("Equipment POL Transfer", a.name)
		doc.adjust_consumed_pol() 
	frappe.db.commit()"""

def list_bb():
        num = 1
        for self in frappe.db.sql("select name, owned_by, equipment, branch, customer_branch from `tabBreak Down Report` where docstatus != 2", as_dict=True):
                if self.owned_by in ['CDCL', 'Own']:
                                eb = frappe.db.get_value("Equipment", self.equipment, "branch")
                                if self.owned_by == "Own" and not self.branch == eb:
                                        print("OWN: " + str(self.name) )
                                        num = num + 1
                                if self.owned_by == "CDCL" and not self.customer_branch == eb:
                                        print("CDCL: " + str(self.name) )
                                        num = num + 1
        print(num)

def clean_br():
	brs = frappe.db.sql("select b.name from `tabBreak Down Report` b, `tabJob Card` j where b.job_card = j.name and j.docstatus = 2 and b.docstatus = 1", as_dict=True)
	for a in brs:
		frappe.db.sql("update `tabBreak Down Report` set job_card = '' where name = %s", a.name)

def pol_entry():
	pols = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabPOL Entry` where reference_name = %s", a.name)
		doc = frappe.get_doc("Issue POL", a.name)
		doc.make_pol_entry()

def ipol_gl():
	pols = frappe.db.sql("select distinct p.name from `tabIssue POL` p, `tabGL Entry` g where p.docstatus = 1 and p.name = g.voucher_no", as_dict=True)
	for a in pols:
		valuation_rate = frappe.db.sql("select valuation_rate from `tabStock Ledger Entry` where voucher_no = %s limit 1", a.name, as_dict=True)
		print(str(a.name))
		if a.name not in ['IPOL180500272']:
			frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
			pol = frappe.get_doc("Issue POL", a.name)
			pol.update_stock_gl_ledger(1, 0, round(valuation_rate[0].valuation_rate, 2))

def asset_cc():
	assets = frappe.db.sql("select name from tabAsset where docstatus = 1", as_dict=True)
	for a in assets:
		doc = frappe.get_doc("Asset", a.name)
		doc.db_set("cost_center", frappe.db.get_value("Employee", doc.issued_to, "cost_center"))
		doc.db_set("branch", frappe.db.get_value("Employee", doc.issued_to, "branch"))

def adjust_ipol():
	pols = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1 and cost_center = 'Construction of 132 KV D/C Transmission Line from Nikachhu to Mangdechhu - CDCL'", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		pol = frappe.get_doc("Issue POL", a.name)
		pol.update_stock_gl_ledger(1, 0)

def adjust_pol():
	pols = frappe.db.sql("select name from tabPOL where fuelbook is not null and docstatus = 1 and cost_center = 'Construction of 132 KV D/C Transmission Line from Nikachhu to Mangdechhu - CDCL'", as_dict=True)
	for a in pols:
		print(str(a.name))
		frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
		pol = frappe.get_doc("POL", a.name)
		pol.update_general_ledger(1)

def migrate_pol_entry():
	pols = frappe.db.sql("select name from `tabEquipment POL Transfer` where docstatus = 1", as_dict=True)
	for a in pols:
		doc = frappe.get_doc("Equipment POL Transfer", a.name)
		print(a.name)
		if not doc.pol_type == "N/A":
			doc.adjust_consumed_pol()

def operators():
	ops = frappe.db.sql("select name from `tabEquipment Operator`", as_dict=True)
	for a in ops:
		doc = frappe.get_doc("Equipment Operator", a.name)
		if doc.employee_type == "Employee":
			name = frappe.db.get_value("Employee", doc.operator, "employee_name")
		if doc.employee_type == "Muster Roll Employee":
			name = frappe.db.get_value("Muster Roll Employee", doc.operator, "person_name")
		doc.db_set("operator_name", name)

def migrate_ipol():
        pols = frappe.db.sql("select name, pol_type from `tabIssue POL` where pol_type in ('Diesel', 'Petrol')", as_dict=True)
        for a in pols:
                print(a.name)
                doc = frappe.get_doc("Issue POL", a.name)
                if a.pol_type == "Diesel":
                        doc.db_set("pol_type", '100452')
                else:
                        doc.db_set("pol_type", '100699')
                item = frappe.get_doc("Item", doc.pol_type)
                doc.db_set("stock_uom" , item.stock_uom)
                doc.db_set("is_hsd_item" , item.is_hsd_item)
                doc.db_set("item_name", item.item_name)
                doc.db_set("posting_date", doc.date)
                doc.db_set("company", 'Construction Development Corporation Ltd')
                doc.db_set("posting_time", '17:13:36')
                doc.db_set("warehouse", get_branch_warehouse(doc.branch))
                doc.db_set("cost_center", get_branch_cc(doc.branch))

                for b in doc.items:
                        d = frappe.get_doc("POL Issue Report Item", b.name)
                        e = frappe.get_doc("Equipment", d.equipment)
			d.db_set("equipment_branch", e.branch)
                        d.db_set("equipment_warehouse", get_branch_warehouse(e.branch))
                        d.db_set("equipment_cost_center", get_branch_cc(e.branch))


def migrate_pol():
        pols = frappe.db.sql("select name, pol_type from `tabPOL` where pol_type in ('Diesel', 'Petrol')", as_dict=True)
        for a in pols:
                print(a.name)
                doc = frappe.get_doc("POL", a.name)
                if a.pol_type == "Diesel":
                        doc.db_set("pol_type", '100452')
                else:
                        doc.db_set("pol_type", '100699')
                item = frappe.get_doc("Item", doc.pol_type)
                doc.db_set("stock_uom" , item.stock_uom)
                doc.db_set("item_name", item.item_name)
                doc.db_set("posting_date", doc.date)
                doc.db_set("company", 'Construction Development Corporation Ltd')
                doc.db_set("posting_time", '17:13:36')
                if doc.book_type == "Common Fuel Book":
                        doc.db_set("book_type", "Common")
                else:
                        doc.db_set("book_type", "Own")

		doc.db_set("warehouse", get_branch_warehouse(doc.branch))
                eqp = frappe.get_doc("Equipment", doc.equipment)
                doc.db_set("equipment_category", eqp.equipment_category)
                doc.db_set("equipment_warehouse", get_branch_warehouse(doc.equipment_branch))
                doc.db_set("fuelbook", "")
                doc.db_set("fuelbook_branch", "")

def post_stock():
	doc = frappe.get_doc("Stock Reconciliation", "SR/000016")
	doc.update_stock_ledger()

def pass_ic_se():
	num = 0
        ses = frappe.db.sql("select name from `tabStock Entry` where purpose = 'Material Transfer' and docstatus = 1 and posting_date >= '2018-01-01'", as_dict=True)
        for a in ses:
                print(a.name)
                doc = frappe.get_doc("Stock Entry", a.name)
                frappe.db.sql("delete from `tabGL Entry` where voucher_no = %s", a.name)
                doc.make_gl_entries()
	print("COMPLETED")

def test():
	from erpnext.custom_utils import round5
	print(round(10.33, 0))
	print(round(10.56, 0))

def cancel_mr_po():
	mrs = frappe.db.sql("select mr.name from `tabMaterial Request` mr where mr.transaction_date < '2018-01-01' and mr.status = 'Cancelled' and mr.workflow_state = 'Approved' and mr.per_ordered = 0 and not exists (select 1 from `tabPurchase Order Item` poi where poi.docstatus != 1 and poi.material_request = mr.name)", as_dict=True)
	for a in mrs:
		if a.name != 'MRSP18010012':
			doc = frappe.get_doc("Material Request", a.name)
			#doc.cancel()
			doc.db_set("workflow_state", "Cancelled")
			print(a.name)

def move_equipment():
	assets = frappe.db.sql("select name from `tabAsset Movement` where docstatus = 1", as_dict=True)
	for a in assets:
		doc = frappe.get_doc("Asset Movement", a.name)
		equipment = frappe.db.get_value("Equipment", {"asset_code": doc.asset}, "name")
		if equipment:
			e = frappe.get_doc("Equipment", equipment)
			if doc.target_custodian:
				branch = frappe.db.get_value("Employee", doc.target_custodian, "branch")
			if doc.target_cost_center:
				branch = frappe.db.get_value("Cost Center", doc.target_cost_center, "branch")
			print(str(equipment) + " : " + str(branch))
			e.db_set("branch", branch)

def cancel_mr():
	mrs = frappe.db.sql("select name from `tabMaterial Request` where docstatus = 2", as_dict=True)
	for a in mrs:
		print(a.name)
		doc = frappe.get_doc("Material Request", a.name)
		doc.db_set("status", "Cancelled")
                doc.db_set("workflow_state", "Cancelled")

def tds_cost_center():
	datas = frappe.db.sql("select a.name as gl, b.name as pi, b.tds_cost_center, b.posting_date from `tabGL Entry` a,`tabPurchase Invoice` b where a.voucher_no = b.name and b.tds_amount > 0 and account like 'Creditors-Other - CDCL' and cost_center is null group by a.name, b.name;", as_dict=True)
	for a in datas:
		doc = frappe.get_doc("GL Entry", a.gl)
		doc.db_set("cost_center", a.tds_cost_center)
		print(str(a.gl) + " ==> " + str(a.tds_cost_center))

def pe_cost_center():
	datas = frappe.db.sql("select pe.name, per.reference_name as pi from `tabPayment Entry Reference` per, `tabPayment Entry` pe where pe.name = per.parent and  pe.paid_to = 'Creditors-Other - CDCL' and pe.docstatus = 1 and pe.payment_type = 'Pay'  group by pe.name;", as_dict=True)
	for a in datas:
		gls = frappe.db.sql("select name from `tabGL Entry` where voucher_no = %s and account = 'Creditors-Other - CDCL' and cost_center is null", a.name, as_dict=True)
		for g in gls:
			doc = frappe.get_doc("GL Entry", g.name)
			cc = frappe.db.get_value("Purchase Invoice", doc.against_voucher, "buying_cost_center")
			if not cc:
				cc = "Pachu Zam Construction - CDCL"
			doc.db_set("cost_center", cc)
			print(str(a.pi) + " :: " + str(g.name) + " ==> " + str(a.name) + " >>> " + str(cc))

def adjust_asset():
        assets = frappe.db.sql("select name, company, branch, cost_center, asset_category, expected_value_after_useful_life, status from tabAsset", as_dict=True)
        for a in assets:
                dep = frappe.db.sql("select name, journal_entry from `tabDepreciation Schedule` where parent = %s and depreciation_amount > 0 order by schedule_date DESC limit 1", (a.name), as_dict=True)
                if dep:
                        obj = frappe.get_doc("Depreciation Schedule", dep[0].name)
                        if a.status == "Fully Depreciated" and flt(a.expected_value_after_useful_life) > 0:
                                js = frappe.db.sql("select name, account, cost_center, credit_in_account_currency, debit_in_account_currency from `tabJournal Entry Account` where parent = %s", dep[0].journal_entry, as_dict=True)
				amount = 0
                                for b in js:
                                        jea = frappe.get_doc("Journal Entry Account", b.name)
                                        dr_or_cr = "credit"
                                        amount = flt(b.credit_in_account_currency)
                                        if flt(b.debit_in_account_currency) > 0:
                                                dr_or_cr = "debit"
                                                amount = flt(b.debit_in_account_currency)
                                        account_curr = str(dr_or_cr) + "_in_account_currency"
					#amount = flt(amount) - flt(a.expected_value_after_useful_life) * 2
                                        #jea.db_set(account_curr, flt(amount) - flt(a.expected_value_after_useful_life) * 2)

				je = frappe.get_doc("Journal Entry", dep[0].journal_entry)
				je.db_set("total_debit", amount)
				je.db_set("total_credit", amount)

                                gls = frappe.db.sql("select name, credit, debit from `tabGL Entry` where voucher_no = %s", dep[0].journal_entry, as_dict=True)
                                for c in gls:
                                        gl = frappe.get_doc("GL Entry", c.name)
                                        dr_or_cr = "credit"
                                        amount = flt(c.credit)
                                        if flt(c.debit) > 0:
                                                dr_or_cr = "debit"
                                                amount = flt(c.debit)
                                        account_curr = str(dr_or_cr) + "_in_account_currency"
                                        #gl.db_set(account_curr, flt(amount) - flt(a.expected_value_after_useful_life) * 2)
                                        #gl.db_set(dr_or_cr, flt(amount) - flt(a.expected_value_after_useful_life) * 2)

                        if flt(a.expected_value_after_useful_life) > 0:
                                cur_value = flt(obj.depreciation_amount) - flt(a.expected_value_after_useful_life) * 2
                                #obj.db_set("depreciation_amount", flt(cur_value))

				        
def consume_trans():
	trans = frappe.db.sql("select name from `tabEquipment POL Transfer` where docstatus = 1", as_dict=True)
	for a in trans:
		b = frappe.get_doc("Equipment POL Transfer", a.name)
		con = frappe.new_doc("Consumed POL")	
		con.equipment = b.from_equipment
		con.branch = b.from_branch
		con.pol_type = b.pol_type
		con.date = b.transfer_date
		con.qty = -1 * flt(b.quantity)
		con.reference_type = "Equipment POL Transfer"
		con.reference_name = b.name
		con.submit()
		con1 = frappe.new_doc("Consumed POL")	
		con1.equipment = b.to_equipment
		con1.branch = b.to_branch
		con1.pol_type = b.pol_type
		con1.date = b.transfer_date
		con1.qty = b.quantity
		con1.reference_type = "Equipment POL Transfer"
		con1.reference_name = b.name
		con1.submit()
		frappe.db.commit()


def consume_pol():
	frappe.db.sql("delete from `tabConsumed POL`")
	frappe.db.commit()

	issues = frappe.db.sql("select name from `tabIssue POL` where docstatus = 1", as_dict=True)
	for a in issues:
		pol = frappe.get_doc("Issue POL", a.name)
		for b in pol.items:
			con = frappe.new_doc("Consumed POL")	
			con.equipment = b.equipment
			con.branch = pol.branch
			con.pol_type = pol.pol_type
			con.date = pol.date
			con.qty = b.qty
			con.reference_type = "Issue POL"
			con.reference_name = pol.name
			con.submit()
			frappe.db.commit()
	
	dcs = frappe.db.sql("select name from `tabPOL` where docstatus = 1 and direct_consumption = 1", as_dict=True)
	for a in dcs:
		b = frappe.get_doc("POL", a.name)
		con = frappe.new_doc("Consumed POL")	
		con.equipment = b.equipment
		con.branch = b.branch
		con.pol_type = b.pol_type
		con.date = b.date
		con.qty = b.qty
		con.reference_type = "POL"
		con.reference_name = b.name
		con.submit()
		frappe.db.commit()

def update_mechanical():
	mps = frappe.db.sql("select name from `tabMechanical Payment` where docstatus = 1", as_dict=True)
	for a in mps:
		acc_name = frappe.db.sql("select account from `tabGL Entry` where voucher_no = %s and debit > 0 and docstatus = 1", (a.name), as_dict=True)
		if acc_name:
			doc = frappe.get_doc("Mechanical Payment", a.name)
			doc.db_set("income_account", acc_name[0].account)
			print(str(acc_name[0].account) + " ==> " + str(a.name))

def ta_attendance():
	all_ta = frappe.db.sql("select name from `tabTravel Authorization` where docstatus = 1", as_dict=True)
	for ta in all_ta:
		ta = frappe.get_doc("Travel Authorization", ta.name)
		d = ta.items[0].date
		if ta.items[len(ta.items) - 1].halt and ta.items[len(ta.items) - 1].till_date:
			e = ta.items[len(ta.items) - 1].till_date
		else:
			e = ta.items[len(ta.items) - 1].date

		days = date_diff(e,d) + 1
		print(str(ta.name) + " ==> " + str(d) + " till " + str(e) + " ::: " + str(days))
		for a in (d + timedelta(n) for n in range(days)):
			al = frappe.db.sql("select name from tabAttendance where docstatus = 1 and employee = %s and att_date = %s", (ta.employee, a), as_dict=True)
			if al:
				doc = frappe.get_doc("Attendance", al[0].name)
				doc.cancel()
			#create attendance
			attendance = frappe.new_doc("Attendance")
			attendance.flags.ignore_permissions = 1
			attendance.employee = ta.employee
			attendance.employee_name = ta.employee_name 
			attendance.att_date = a
			attendance.status = "Tour"
			attendance.branch = ta.branch
			attendance.company = frappe.db.get_value("Employee", ta.employee, "company")
			attendance.reference_name = ta.name
			attendance.submit()

def add_days_test():
	all_att = frappe.db.sql("select name from `tabLeave Application` where docstatus = 1", as_dict=True)
	for att in all_att:
		print(att.name)
		self = frappe.get_doc("Leave Application", att.name) 
		d = getdate(self.from_date)
		e = getdate(self.to_date)
		days = date_diff(e, d) + 1
		for a in (d + timedelta(n) for n in range(days)):
			if getdate(a).weekday() != 6:
				#create attendance
				attendance = frappe.new_doc("Attendance")
				attendance.flags.ignore_permissions = 1
				attendance.employee = self.employee
				attendance.employee_name = self.employee_name 
				attendance.att_date = a
				attendance.status = "Leave"
				attendance.branch = self.branch
				attendance.company = self.company
				attendance.reference_name = self.name
				attendance.submit()

def assign_branch_att():
	atts = frappe.db.sql("select name, employee from `tabAttendance` where docstatus = 1", as_dict=True)
	for a in atts:
		emp = frappe.db.get_value("Employee", a.employee, "branch")
		doc = frappe.get_doc("Attendance", a.name)
		doc.db_set("branch", emp)

def assign_date_ta():
	tas = frappe.db.sql("select name from `tabTravel Authorization` where travel_claim is null", as_dict=True)
	for ta in tas:
		taa = frappe.db.sql("select name, date from `tabTravel Authorization Item` where parent = %s order by date desc limit 1", (str(ta.name)), as_dict=True)
		doc = frappe.get_doc("Travel Authorization", ta.name)
		#doc.db_set('end_date_auth', taa[0].date)
		print(str(ta.name) + " ==> " + str(taa[0].date) + "  ==> " + str(doc.end_date_auth))

def adjust_leave_encashment():
        les = frappe.db.sql("select name, encashed_days, employee from `tabLeave Encashment` where docstatus = 1 and application_date between %s and %s", ('2017-01-01', '2017-12-31'), as_dict=True)
        for le in les:
                print(str(le.name))
                allocation = frappe.db.sql("select name, to_date from `tabLeave Allocation` where docstatus = 1 and employee = %s and leave_type = 'Earned Leave' order by to_date desc limit 1", (le.employee), as_dict=True)
                obj = frappe.get_doc("Leave Allocation", allocation[0].name)
                obj.db_set("leave_encashment", le.name)
                obj.db_set("encashed_days", (le.encashed_days))
                obj.db_set("total_leaves_allocated", (flt(obj.total_leaves_allocated) - flt(le.encashed_days)))

def get_date():
	print(now())
def update_ss():
	sss = frappe.db.sql("select name from `tabSalary Structure`", as_dict=True)
	for ss in sss:
		doc = frappe.get_doc("Salary Structure", ss)
		doc.save()

def update_customer():
	ccs = frappe.db.sql("select name from `tabCost Center` where is_group != 1", as_dict=True)
	for cc in ccs:
		obj = frappe.get_doc("Cost Center", cc)
		print(cc)
		obj.save()

def update_employee():
	emp_list = frappe.db.sql("select name from tabEmployee", as_dict=True)
	for emp in emp_list:
		print(emp.name)
		edoc = frappe.get_doc("Employee", emp)
		branch = frappe.db.get_value("Cost Center", edoc.cost_center, "branch")
		if branch:
			edoc.branch = branch
			edoc.save()
		else:
			frappe.throw("No branch for " + str(edoc.cost_center) + " for " + str(emp))

def give_admin_access():
	reports = frappe.db.sql("select name from tabReport", as_dict=True)
	for r in reports:
		role = frappe.new_doc("Report Role")
		role.parent = r.name
		role.parenttype = "Report"
		role.parentfield = "roles"
		role.role = "Administrator"
		role.save()		

def save_equipments():
	for a in frappe.db.sql("select name from tabEquipment", as_dict=True):
		doc = frappe.get_doc("Equipment", a.name)
		print(str(a))
		doc.save()

def submit_ss():
	ss = frappe.db.sql("select name from `tabSalary Structure`", as_dict=True)
	for s in ss:
		doc = frappe.get_doc("Salary Structure", s.name)
		for a in doc.earnings:
			if a.salary_component == "Basic Pay":
				print(str(doc.employee) + " ==> " + str(a.amount))
				update_salary_structure(doc.employee, flt(a.amount), s.name)
				break
		#doc.save()

def create_users():
	emp = frappe.db.sql("select name, company_email from tabEmployee where status = 'Active'", as_dict=True)
	if emp:
		for e in emp:
			print(str(e.name))
			doc = frappe.new_doc("User")
			doc.enabled = 1
			doc.email = e.company_email
			doc.first_name = "Test"
			doc.new_password = "CDCL!2017"
			doc.save()
		
			role = frappe.new_doc("UserRole")
			role.parent = doc.name
			role.role = "Employee"
			role.parenttype = "User"
			role.save()
			doc.save()
			em = frappe.get_doc("Employee", e.name)	
			em.user_id = doc.name
			em.save()
		print("DONE")

def submit_assets():
	list = frappe.db.sql("select name from tabAsset where docstatus = 0", as_dict=True)
	if list:
		num = 0
		for a in list:
			num = num + 1
			doc = frappe.get_doc("Asset", a.name)
			doc.submit()
			print(str(a.name))
			if cint(num) % 100 == 0:
				frappe.db.commit()
		print("DONE")

def give_permission():
	users = frappe.db.sql("select name from tabUser", as_dict=True)
	for u in users:
		if u.name in ['admins@cdcl.bt', 'proco@cdcl.bt', 'accounts@cdcl.bt', 'project@cdcl.bt', 'maintenance@cdcl.bt', 'fleet@cdcl.bt', 'sales@cdcl.bt','stock@cdcl.bt', 'hr@cdcl.bt','tashi.dorji775@bt.bt', 'sonam.zangmo@bt.bt', 'siva@bt.bt', 'jigme@bt.bt', 'dorji2392@bt.bt', 'sangay.dorji2695@bt.bt', 'lhendrup.dorji@bt.bt']:
			for branch in frappe.db.sql("select name from tabBranch", as_dict=True):
				#if branch == 'Lingmethang':
				frappe.permissions.add_user_permission("Branch", branch.name, u.name)
			print("DONE")	
		print(str(u))

##
# Post earned leave on the first day of every month
##
def post_earned_leaves():
	date = add_years(frappe.utils.nowdate(), 1)
	start = get_first_day(date);
	end = get_last_day(date);
	
	employees = frappe.db.sql("select name, employee_name from `tabEmployee` where status = 'Active' and employment_type in (\'Regular\', \'Contract\')", as_dict=True)
	for e in employees:
		la = frappe.new_doc("Leave Allocation")
		la.employee = e.name
		la.employee_name = e.employee_name
		la.leave_type = "Casual Leave"
		la.from_date = str(start)
		la.to_date = str(end)
		la.carry_forward = cint(0)
		la.new_leaves_allocated = flt(10)
		la.submit()
		
#Create asset received entries for asset balance
def createAssetEntries():
	frappe.db.sql("delete from `tabAsset Received Entries`")
	receipts = frappe.db.sql("select pr.posting_date, pr.name, pri.item_code, pri.qty from `tabPurchase Receipt` pr,  `tabPurchase Receipt Item` pri  where pr.docstatus = 1 and pri.docstatus = 1 and pri.parent = pr.name", as_dict=True)
	for a in receipts:
		item_group = frappe.db.get_value("Item", a.item_code, "item_group")
		if item_group and item_group == "Fixed Asset":
			ae = frappe.new_doc("Asset Received Entries")
			ae.item_code = a.item_code
			ae.qty = a.qty
			ae.received_date = a.posting_date
			ae.ref_doc = a.name
			ae.submit()

# create consumed and committed budget
def budget():
	deleteExisting()
	commitBudget();
	consumeBudget();
	adjustBudgetJE()

def deleteExisting():
	print("Deleting existing data")
	frappe.db.sql("delete from `tabCommitted Budget`")
	frappe.db.sql("delete from `tabConsumed Budget`")

##
# Commit Budget
##
def commitBudget():
	print("Committing budgets from PO")
	orders = frappe.db.sql("select name from `tabPurchase Order` where docstatus = 1", as_dict=True)
	for a in orders:
		order = frappe.get_doc("Purchase Order", a['name'])
		for item in order.get("items"):
			account_type = frappe.db.get_value("Account", item.budget_account, "account_type")
			if account_type in ("Fixed Asset", "Expense Account"):
				consume = frappe.get_doc({
					"doctype": "Committed Budget",
					"account": item.budget_account,
					"cost_center": item.cost_center,
					"po_no": order.name,
					"po_date": order.transaction_date,
					"amount": item.amount,
					"poi_name": item.name,
					"item_code": item.item_code,
					"date": frappe.utils.nowdate()})
				consume.submit()


##
# Commit Budget
##
def adjustBudgetJE():
	print("Committing and consuming from JE")
	entries = frappe.db.sql("select name from `tabGL Entry` where voucher_type='Journal Entry' and (against_voucher_type != 'Asset' or against_voucher_type is null)", as_dict=True)
	for a in entries:
		gl = frappe.get_doc("GL Entry", a['name'])
		account_type = frappe.db.get_value("Account", gl.account, "account_type")
		
		if account_type in ("Fixed Asset", "Expense Account"):
			commit = frappe.get_doc({
					"doctype": "Committed Budget",
					"account": gl.account,
					"cost_center": gl.cost_center,
					"po_no": gl.voucher_no,
					"po_date": gl.posting_date,
					"amount": gl.debit - gl.credit,
					"item_code": "",
					"date": frappe.utils.nowdate()})
			commit.submit()
			
			consume = frappe.get_doc({
					"doctype": "Consumed Budget",
					"account": gl.account,
					"cost_center": gl.cost_center,
					"po_no": gl.voucher_no,
					"po_date": gl.posting_date,
					"amount": gl.debit - gl.credit,
					"item_code": "",
					"com_ref": gl.voucher_no,
					"date": frappe.utils.nowdate()})
			consume.submit()

##
# Commit Budget
##
def consumeBudget():
	print("Consuming budgets from PI")
	invoices = frappe.db.sql("select name from `tabPurchase Invoice` where docstatus = 1", as_dict=True)
	for a in invoices:
		invoice = frappe.get_doc("Purchase Invoice", a['name'])
		for item in invoice.get("items"):
			expense, cost_center = frappe.db.get_value("Purchase Order Item", item.po_detail, ["budget_account", "cost_center"])
			if expense:
				account_type = frappe.db.get_value("Account", expense, "account_type")
				if account_type in ("Fixed Asset", "Expense Account"):
					po_date = frappe.db.get_value("Purchase Order", item.purchase_order, "transaction_date")
					consume = frappe.get_doc({
						"doctype": "Consumed Budget",
						"account": expense,
						"cost_center": item.cost_center,
						"po_no": invoice.name,
						"po_date": po_date,
						"amount": item.amount,
						"pii_name": item.name,
						"item_code": item.item_code,
						"com_ref": item.purchase_order,
						"date": frappe.utils.nowdate()})
					consume.submit()
	

##
# Update presystem date
##
def updateDate():
	import csv
	with open('/home/frappe/emines/sites/emines.smcl.bt/public/files/myasset.csv', 'rb') as f:
		reader = csv.reader(f)
		mylist = list(reader)
		for i in mylist:
			asset = frappe.get_doc("Asset", i[0])
			asset.db_set("presystem_issue_date", i[1])
			
		print ("DONE")
##
# Sets the initials of autoname for PO, PR, SO, SI, PI, etc
##
def moveConToCom():
	pass
	consumed = frappe.get_all("Consumed Budget")
	to = len(consumed)
	i = 0
	for a in consumed:
		i = i + 1
		d = frappe.get_doc("Consumed Budget", a.name)
		obj = frappe.get_doc({
				"doctype": "Committed Budget",
				"account": d.account,
				"cost_center": d.cost_center,
				"po_no": d.po_no,
				"po_date": d.po_date,
				"amount": d.amount,
				"item_code": d.item_code,
				"date": d.date
			})
		obj.submit()
		d.delete();
		print(str(i * 100 / to))
	print("DONE")

def createConsumed():
	con = frappe.db.sql("select pe.name as name, per.reference_name as pi from `tabPayment Entry Reference` per, `tabPayment Entry` pe where per.parent = pe.name and pe.docstatus = 1 and per.reference_doctype = 'Purchase Invoice' and pe.posting_date between '2017-01-01' and '2017-12-31'", as_dict=True)
	for a in con:
		items = frappe.db.sql("select item_code, cost_center, purchase_order, amount from `tabPurchase Invoice Item`  where docstatus = 1 and parent = \'" + str(a.pi) + "\'", as_dict=True)
		for i in items:
			#con = frappe.db.sql("select name, po_no, amount, docstatus from `tabCommitted Budget` where po_no = \'" + i.purchase_order + "\' and item_code = \'" + i.item_code + "\' and cost_center = \'" + i.cost_center + "\'")
			con = frappe.db.sql("select name, po_no, amount, account from `tabCommitted Budget` where po_no = \'" + i.purchase_order + "\' and item_code = \'" + i.item_code + "\' and cost_center = \'" + i.cost_center + "\' and amount = \'" + str(i.amount) + "\'")
			print(str(a.name))
			if con:
				print(str(con))
			else:
				print("NOT FOUND")
			#print(str(i.purchase_order) + " / " + str(i.item_code) + " / " + str(i.amount))


# /home/frappe/erp bench execute erpnext.custom_patch.grant_permission_all_test
def grant_permission_all_test():
        emp_list = frappe.db.sql("""
                                 select company, branch, name as employeecd, user_id, 'Employee' type
                                 from `tabEmployee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabEmployee`.user_id)
                                and name = 'CDCL0403003'
                        """, as_dict=1)

        for emp in emp_list:
                # From Employee Master
                frappe.permissions.remove_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.remove_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.add_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.add_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.remove_user_permission(emp.type, emp.employeecd, emp.user_id)
                frappe.permissions.add_user_permission(emp.type, emp.employeecd, emp.user_id)
                
                # From Assign Branch 
                ba = frappe.db.sql("""
                                select branch
                                from `tabBranch Item`
                                where exists(select 1
                                               from `tabAssign Branch`
                                               where `tabAssign Branch`.name = `tabBranch Item`.parent
                                               and   `tabAssign Branch`.user = '{0}')
                        """.format(emp.user_id), as_dict=1)
                

                for a in ba:
                        frappe.permissions.remove_user_permission("Branch", a.branch, emp.user_id)
                        frappe.permissions.add_user_permission("Branch", a.branch, emp.user_id)


def grant_permission_all():
        emp_list = frappe.db.sql("""
                                 select company, branch, name as employeecd, user_id, 'Employee' type
                                 from `tabEmployee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabEmployee`.user_id)
                                union all
                                select company, branch, name as employeecd, user_id, 'GEP Employee' type
                                 from `tabGEP Employee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabGEP Employee`.user_id)
                                union all
                                select company, branch, name as employeecd, user_id, 'Muster Roll Employee' type
                                 from `tabMuster Roll Employee`
                                 where user_id is not null
                                 and exists(select 1
                                                from  `tabUser`
                                                where `tabUser`.name = `tabMuster Roll Employee`.user_id)
                        """, as_dict=1)

        for emp in emp_list:
                # From Employee Master
                frappe.permissions.remove_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.remove_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.add_user_permission("Company", emp.company, emp.user_id)
                frappe.permissions.add_user_permission("Branch", emp.branch, emp.user_id)

                frappe.permissions.remove_user_permission(emp.type, emp.employeecd, emp.user_id)
                frappe.permissions.add_user_permission(emp.type, emp.employeecd, emp.user_id)
                                                
                # From Assign Branch 
                ba = frappe.db.sql("""
                                select branch
                                from `tabBranch Item`
                                where exists(select 1
                                               from `tabAssign Branch`
                                               where `tabAssign Branch`.name = `tabBranch Item`.parent
                                               and   `tabAssign Branch`.user = '{0}')
                        """.format(emp.user_id), as_dict=1)
                

                for a in ba:
                        frappe.permissions.remove_user_permission("Branch", a.branch, emp.user_id)
                        frappe.permissions.add_user_permission("Branch", a.branch, emp.user_id)

def remove_memelakha_entries():
	# This is done after manually crosschecking, everything is ok
	il = frappe.db.sql("""
		select a.name, b.item_code, count(*), sum(b.qty)
		from `tabStock Entry` a, `tabStock Entry Detail` b
		where a.branch = 'Memelakha Asphalt Plant' 
		and b.parent = a.name
		and a.job_card is null
		and a.name not in ('SECO17100009')
		and a.purpose = 'Material Issue'
		and lower(title) not like '%asphalt%'
		group by a.name, b.item_code
		order by a.name, b.item_code;
		""", as_dict=1)
	
	counter = 0

	for i in il:
		counter += 1
		idoc = frappe.get_doc("Stock Entry", i.name)
		print counter, idoc.name, idoc.docstatus

# 25/12/2017 SHIV, It is observed that parent cost_centers are used in the transaction which is wrong
def check_for_cc_group_entries():
        ex = ['Cost Center','Attendance Tool Others','Budget Reappropriation Tool','Project Overtime Tool', 'Supplementary Budget Tool']

        li = frappe.db.sql("""
                        select g.doctype, g.fieldname, g.table_name
                        from (
                        
                                select
                                        parent as doctype,
                                        fieldname,
                                        'tabDocField' as table_name
                                from `tabDocField` 
                                where (
                                        (fieldtype = 'Link' and options = 'Cost Center')
                                        or
                                        (lower(fieldname) like '%cost%center%' and fieldtype in ('Data','Dynamic Link','Small Text','Long Text','Read Only', 'Text'))
                                        )
                                union all
                                select
                                        dt as doctype,
                                        fieldname,
                                        'tabCustom Field' as table_name
                                from `tabCustom Field` 
                                where (
                                        (fieldtype = 'Link' and options = 'Cost Center')
                                        or
                                        (lower(fieldname) like '%cost%center%' and fieldtype in ('Data','Dynamic Link','Small Text','Long Text','Read Only', 'Text'))
                                        )
                        ) as g
                        where g.doctype not in ({0})
                """.format("'"+"','".join(ex)+"'"), as_dict=1)

        for i in li:
                no_of_rec = 0
                
                counts = frappe.db.sql("""
                                select a.{1} cc, count(*) counts
                                from `tab{0}` as a
                                where a.{1} is not null
                                and exists(select 1
                                                from `tabCost Center` as b
                                                where b.name = a.{1}
                                                and b.is_group = 1)
                                group by a.{1}
                """.format(i.doctype, i.fieldname), as_dict=1)

                '''
                if counts:
                        if counts[0].counts > 0:
                                no_of_rec = counts[0].counts
                                print i.doctype+" ("+i.fieldname+") : "+str(no_of_rec)
                '''

                for c in counts:
                        print i.doctype.ljust(50,' ')+str(":"), c.cc, c.counts
                
#bench execute erpnext.custom_patch.el_allocation --args 'CDCL0005001','no'
def el_allocation(employee=None):
        # Allocating missed out 5days EL for Hesothangkha for 01/01/17-30/09/17
        print 'employee', employee

        cond = ""
        
        if employee:
                cond = "and employee = '{0}'".format(employee)
                
        li = frappe.db.sql("""
                select name, employee, from_date, to_date,
                        new_leaves_allocated,
                        carry_forwarded_leaves,
                        total_leaves_allocated,
                        leave_type
                from `tabLeave Allocation` as la
                where la.leave_type = 'Earned Leave'
                and from_date = '2017-01-01'
                and to_date = '2017-09-30'
                and exists(select 1
                             from `tabEmployee Internal Work History` as e
                            where e.branch = 'Hesothangkha'
                              and e.parent = la.employee)
                and docstatus = 1
                {cond}
                order by employee
                """.format(cond=cond), as_dict=True)

        '''
        for i in li:
                cf = flt(i.carry_forwarded_leaves)+5.0 if flt(i.carry_forwarded_leaves)+5.0 <= 60.0 else 60.0
                ta = flt(i.total_leaves_allocated)+5.0 if flt(i.total_leaves_allocated)+5.0 <= 60.0 else 60.0
                
                frappe.db.sql("""
                                update `tabLeave Allocation`
                                set carry_forwarded_leaves = {0}, total_leaves_allocated = {1}
                                where name = '{2}'
                        """.format(flt(cf), flt(ta), i.name))
        '''

        counter = 0
        for i in li:
                counter += 1
                print counter,'|', i.employee,'|', i.from_date,'|', i.to_date,'|', i.new_leaves_allocated,'|', i.carry_forwarded_leaves,'|', i.total_leaves_allocated

                # New allocations
                na = frappe.db.sql("""
                        select name, employee, from_date, to_date,
                                new_leaves_allocated,
                                carry_forwarded_leaves,
                                total_leaves_allocated,
                                leave_type
                          from `tabLeave Allocation`
                         where employee   = '{0}'
                           and leave_type = '{1}'
                           and docstatus  = 1
                           and from_date  > '{2}'
                         order by from_date, to_date
                        """.format(i.employee, i.leave_type, i.to_date), as_dict=True)

                for a in na:
                        print counter,'|',a.employee,'|', a.from_date,'|', a.to_date,'|', a.new_leaves_allocated,'|', a.carry_forwarded_leaves,'|', a.total_leaves_allocated

                        '''
                        cf = flt(a.carry_forwarded_leaves)+5.0 if flt(a.carry_forwarded_leaves)+5.0 <= 60.0 else 60.0
                        ta = flt(a.total_leaves_allocated)+5.0 if flt(a.total_leaves_allocated)+5.0 <= 60.0 else 60.0

                        print cf, ta

                        frappe.db.sql("""
                                update `tabLeave Allocation`
                                set carry_forwarded_leaves = {0}, total_leaves_allocated = {1}
                                where name = '{2}'
                        """.format(flt(cf), flt(ta), a.name))
                        '''

# /home/frappe/erp bench execute erpnext.custom_patch.refresh_salary_structure
def refresh_salary_structure():
        ss = frappe.db.sql("select name from `tabSalary Structure` where is_active='Yes'", as_dict=True)
        counter = 0
	for s in ss:
		doc = frappe.get_doc("Salary Structure", s.name)
		for a in doc.earnings:
			if a.salary_component == "Basic Pay":
                                counter += 1
                                print counter,s.name
				update_salary_structure(doc.employee, flt(a.amount), s.name)
				break

# /home/frappe/erp bench execute erpnext.custom_patch.update_project_invoice
# Refreshing fields uptodate_quantity, uptodate_rate, uptodate_amount
def update_project_invoice():
        bi = frappe.db.sql("""
                select t2.name, t2.parent, t1.invoice_date, t2.boq_item_name, t1.modified
                from `tabProject Invoice BOQ` as t2, `tabProject Invoice` as t1
                where t2.parent = t1.name
                and ifnull(t2.is_group,0) = 0
                and t1.docstatus != 2
                order by t1.project, t1.invoice_date
        """, as_dict=1)

        counter = 0
        for i in bi:
                counter += 1
                uptodate_quantity = 0.0
                uptodate_rate     = 0.0
                uptodate_amount   = 0.0
                
                tot = frappe.db.sql("""
                        select
                                sum(ifnull(invoice_quantity,0)) as invoice_quantity,
                                max(ifnull(invoice_quantity,0)) as invoice_rate,
                                sum(ifnull(invoice_amount,0))   as invoice_amount
                        from `tabProject Invoice BOQ` as t2, `tabProject Invoice` as t1
                        where t2.parent = t1.name
                        and t2.boq_item_name = '{0}'
                        and t2.is_selected = 1
                        and t2.docstatus = 1
                        and t1.invoice_date <= '{1}'
                        and t1.modified < '{2}'
                """.format(i.boq_item_name, i.invoice_date, i.modified), as_dict=1)

                if tot:
                        uptodate_quantity = flt(tot[0].invoice_quantity)
                        uptodate_rate     = flt(tot[0].invoice_rate)
                        uptodate_amount   = flt(tot[0].invoice_amount)

                frappe.db.sql("""
                        update `tabProject Invoice BOQ`
                        set uptodate_quantity = {1},
                                uptodate_rate = {2},
                                uptodate_amount = {3}
                        where name = '{0}'
                """.format(i.name, uptodate_quantity, uptodate_rate, uptodate_amount))
                print counter

# /home/frappe/erp bench execute erpnext.custom_patch.add_mr_creator_role
# Adding back MR Creator role, 2018/07/26
def add_mr_creator_role():
        li = frappe.db.sql("""
                select distinct(t1.owner) as owner
                from `tabMaterial Request` as t1
                where t1.creation >= '2018-03-01'
                and not exists(select 1
                               from `tabUserRole` as t2
                               where t2.parent = t1.owner
                               and t2.role = 'MR Creator')
        """, as_dict=1)
        
        counter = 0
        for i in li:
                counter += 1
                user = frappe.get_doc("User", i.owner)
                user.flags.ignore_permissions = True
                user.add_roles("MR Creator")
                print counter, i.owner

#
# by SHIV on 2018/08/10
# Updating to_date in production from backup taken on 2018/08/08 12:00PM        
#
def update_hire_charge_parameter():
	li = frappe.db.sql("""
		select *
		from `tabHire Charge Item_temp` as t1
		where exists(select 1
				from `tabHire Charge Item_bkup20180810` as t2
				where t2.name = t1.name
				and date_format(t2.modified,'%H:%i') = '14:24') 
	""", as_dict=1)

	counter = 0
	for i in li:
		counter += 1
		print counter, i.name