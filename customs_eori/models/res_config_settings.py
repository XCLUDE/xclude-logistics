# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    eori_validation = fields.Boolean(related='company_id.eori_validation', readonly=False, string='Verify EORI Number')
