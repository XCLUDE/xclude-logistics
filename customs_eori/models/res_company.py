from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    eori_number = fields.Char(
        string="EORI Number",
        help="Economic Operator Registration and Identification Number used for customs identification in EU and GB."
    )
    eori_validation = fields.Boolean(string='Verify EORI Numbers')
