# -*- coding: utf-8 -*-

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.tools.misc import formatLang

from odoo.exceptions import UserError, RedirectWarning, ValidationError

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def _get_assays(self, coa_id, contract_id):
        corrective_factor = contract_id.corrective_factor
        base_price_components = self.env['sale.contract.base.price.component'].sudo().search( [( 'sale_contract_id', '=', contract_id.id )] )
        price_component_dict = {
            'main':[],
            'add':[],
            'subtract':[],
        }
        for base_price_component in base_price_components :
            _logger.warning( base_price_component )
            if price_component_dict.get( base_price_component.rule, False):
                price_component_dict[ base_price_component.rule ] += [ base_price_component ]
            else:
                price_component_dict[ base_price_component.rule ] = []
                price_component_dict[ base_price_component.rule ] += [ base_price_component ]
        
        assay_rows = []
        if price_component_dict[ 'main' ] :
            main = price_component_dict[ 'main' ][0]
            main_spec_qaqc = 0
            for element_spec in coa_id.element_specs :
                if element_spec.element_id.id == main.element_id.id :
                    main_spec_qaqc = element_spec.spec
                    assay_rows += [{
                        "name" : element_spec.element_id.name,
                        "value" : element_spec.spec,
                    }]
            diff = main_spec_qaqc - main.spec
            corrective_factor = corrective_factor + ( diff * 10 ) 

            for component_add in price_component_dict[ 'add' ] :
                for element_spec in coa_id.element_specs :
                    if element_spec.element_id.id == component_add.element_id.id :
                        assay_rows += [{
                            "name" : element_spec.element_id.name,
                            "value" : element_spec.spec,
                        }]

            for component_subtract in price_component_dict[ 'subtract' ] :
                for element_spec in coa_id.element_specs :
                    if element_spec.element_id.id == component_subtract.element_id.id :
                        assay_rows += [{
                            "name" : element_spec.element_id.name,
                            "value" : element_spec.spec,
                        }]


        return {
            "corrective_factor" : corrective_factor,
            "assay_rows" : assay_rows,
        }



    @api.multi
    def _get_detailed_data(self):
        self.ensure_one()
        res = {}
        res["name"] = ""
        res["cf"] = ""
        # try:
        sale_order = self.env['sale.order'].sudo().search( [ ("name", "=", self.origin) ], limit=1 )
        coa_id = sale_order.coa_id
        contract_id = sale_order.contract_id
        shipping_id = sale_order.shipping_id
        assays = self._get_assays( coa_id, contract_id )
        res["cf"] = assays["corrective_factor"]
        res["assay_rows"] = assays["assay_rows"]
        res["qty"] = '{:,}'.format(shipping_id.quantity)

        date = datetime.strptime( sale_order.date_order, '%Y-%m-%d %H:%M:%S')
        res["hma"] =  "HMA " + date.strftime("%B") +" "+ date.strftime("%Y") + " IDR " + '{:,}'.format( sale_order.hma_price )
        res["hpm"] = '{:,}'.format( sale_order.hpm_price - contract_id.shipping_price )
        res["shipping_cost"] = '{:,}'.format( contract_id.shipping_price )
        res["cif_price"] = '{:,}'.format( sale_order.hpm_price )
        res["base_price_txt"] = "Kurs " + date.strftime("%Y") + " IDR " + '{:,}'.format( sale_order.currency ) + " x USD " + res["cif_price"]
        res["base_price"] = '{:,}'.format( round( sale_order.hpm_price * sale_order.currency, 0 ) )


        # except:
        #     _logger.warning("Something went wrong")
        # finally:
        #     _logger.warning("The 'try except' is finished") 
        

        return res

    @api.multi
    def invoice_print(self):
        res = super(AccountInvoice, self).invoice_print()

        self.ensure_one()
        self.sent = True
        return self.env['report'].get_action(self, 'mining_invoice_report.report_mining_invoice')
        # return self.env['report'].get_action(self, 'account.report_invoice')
    
    @api.multi
    def action_invoice_draft(self):
        if self.filtered(lambda inv: inv.state != 'cancel'):
            raise UserError(_("Invoice must be cancelled in order to reset it to draft."))
        # go from canceled state to draft state
        self.write({'state': 'draft', 'date': False})
        # Delete former printed invoice
        try:
            report_invoice = self.env['report']._get_report_from_name('account.report_invoice')
        except IndexError:
            report_invoice = False
        if report_invoice and report_invoice.attachment:
            for invoice in self:
                with invoice.env.do_in_draft():
                    invoice.number, invoice.state = invoice.move_name, 'open'
                    attachment = self.env['report']._attachment_stored(invoice, report_invoice)[invoice.id]
                if attachment:
                    attachment.unlink()
        return True
