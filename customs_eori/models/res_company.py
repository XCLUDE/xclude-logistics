from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    eori_validation = fields.Boolean(string='Verify EORI Numbers')
