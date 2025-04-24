# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    eori_validation = fields.Boolean(string='Verify EORI Numbers')
    eori_number = fields.Char(related='partner_id.eori_number', string="EORI Number", readonly=False)
