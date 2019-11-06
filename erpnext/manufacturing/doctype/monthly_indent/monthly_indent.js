// Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Monthly Indent', {
	refresh: function(frm) {

	}
});

frappe.ui.form.on("Indent Detail", {
        "price_list": function(frm, cdt, cdn) {
                d = locals[cdt][cdn]
        	loc = "NA"       
                frappe.call({
                        method: "erpnext.selling.doctype.selling_price.selling_price.get_selling_rate",
                        args: {
              			"price_list": d.price_list,                  
                                "branch": cur_frm.doc.branch,
                                "item_code": d.item_code,
                                "transaction_date": cur_frm.doc.posting_date,
                        	"location": loc
			},
                        callback: function(r) {
                                frappe.model.set_value(cdt, cdn, "rate", r.message)
                                cur_frm.refresh_field("rate")
                        }
                })
        },
	"quantity": function(frm, cdt, cdn) {
		d= locals[cdt] [cdn]
                frappe.model.set_value(cdt, cdn, "amount", d.quantity * d.rate)
}


})