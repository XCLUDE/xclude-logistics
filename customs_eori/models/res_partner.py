from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from zeep import Client as ZeepClient
import http.client
import json
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    eori_validation_state = fields.Selection([
        ('unchecked', 'Unchecked'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
    ], string='EORI Validation State', default='unchecked', readonly=True)
    
    eori_number = fields.Char(
        string="EORI Number",
        help="Economic Operator Registration and Identification Number used for customs identification in EU and GB."
    )

    def _split_eori(self, eori):
        return eori[:2].upper(), eori[2:].replace(' ', '')

    def _is_eori_valid(self):
        """Returns True/False based on validation result only (no chatter)."""
        if not self.eori_number:
            return False
        eori_country, eori_number = self._split_eori(self.eori_number)
        full_number = eori_country + eori_number
        eori_valid = False

        if eori_country in ['GB', 'XI']:
            eori_valid = self._validate_eori_gb(full_number)
        else:
            country = self.env['res.country'].search([('code', '=', eori_country)], limit=1)
            europe = self.env.ref('base.europe', raise_if_not_found=False) or \
                     self.env['res.country.group'].search([('name', '=', 'Europe')], limit=1)
            if country and europe and country.id in europe.country_ids.ids:
                eori_valid = self._validate_eori_eu(full_number)

        return eori_valid

    def validate_and_log_eori(self):
        """Call this method to validate, set state, and post message in chatter."""
        for partner in self:
            if not partner.eori_number:
                partner.eori_validation_state = 'unchecked'
                continue
            is_valid = partner._is_eori_valid()
            partner.eori_validation_state = 'valid' if is_valid else 'invalid'
            msg = _("Valid EORI Number: <b>%s</b>") if is_valid else _("Invalid EORI Number: <b>%s</b>")
            partner.message_post(body=msg % partner.eori_number, message_type="comment")

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_eu(self, eori):
        try:
            client = ZeepClient('https://ec.europa.eu/taxation_customs/dds2/eos/validation/services/validation?wsdl')
            result = client.service.validateEORI(eori)
            return result['result'][0]['statusDescr'] == 'Valid'
        except Exception as e:
            _logger.warning("EU EORI validation failed for %s: %s", eori, e)
            return False

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_gb(self, eori):
        try:
            connection = http.client.HTTPSConnection('api.service.hmrc.gov.uk')
            connection.request(
                'POST',
                '/customs/eori/lookup/check-multiple-eori',
                json.dumps({'eoris': [eori]}),
                {'Content-type': 'application/json'}
            )
            response = connection.getresponse()
            if response.status != 200:
                _logger.warning("HMRC EORI response status: %s", response.status)
                return False
            answer = json.loads(response.read().decode())
            return answer[0].get('valid') is True
        except Exception as e:
            _logger.warning("GB EORI validation failed for %s: %s", eori, e)
            return False

    def write(self, vals):
        res = super().write(vals)
        if 'eori_number' in vals and self.env.company.eori_validation:
            self.filtered(lambda p: p.eori_number).validate_and_log_eori()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if self.env.company.eori_validation:
            records.filtered(lambda p: p.eori_number).validate_and_log_eori()
        return records
