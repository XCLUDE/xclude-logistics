from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.tools.zeep import ZeepClient
import http.client
import json
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    eori_number = fields.Char(
        string="EORI Number",
        help="Economic Operator Registration and Identification Number used for customs identification in EU and GB."
    )

    def _split_eori(self, eori):
        """Split into country prefix and actual number."""
        return eori[:2].upper(), eori[2:].replace(' ', '')

    @api.constrains('eori_number')
    def _check_eori_number(self):
        """Validates EORI if company has validation enabled."""
        if not self.env.company.eori_validation:
            return

        for partner in self:
            if partner.eori_number:
                try:
                    if not self._validate_eori(partner.eori_number):
                        raise ValidationError(_('Invalid EORI Number: %s') % partner.eori_number)
                except Exception as e:
                    _logger.exception("EORI validation error for %s: %s", partner.name, e)
                    raise ValidationError(_('EORI validation could not be completed.'))

    def _validate_eori(self, full_eori_number):
        eori_country, eori_number = self._split_eori(full_eori_number)

        if eori_country in ['GB', 'XI']:
            return self._validate_eori_gb(eori_country + eori_number)

        country = self.env['res.country'].search([('code', '=', eori_country)], limit=1)
        europe = self.env.ref('base.europe') or self.env['res.country.group'].search([('name', '=', 'Europe')], limit=1)

        if country and europe and country.id in europe.country_ids.ids:
            return self._validate_eori_eu(eori_country + eori_number)

        return False

    @tools.ormcache('eori')
    def _validate_eori_eu(self, eori):
        """EU validation using Odoo's ZeepClient."""
        try:
            client = ZeepClient('https://ec.europa.eu/taxation_customs/dds2/eos/validation/services/validation?wsdl')
            result = client.service.validateEORI(eori)
            return result['result'][0]['statusDescr'] == 'Valid'
        except Exception as e:
            _logger.warning("EU EORI validation failed for %s: %s", eori, e)
            return False

    @tools.ormcache('eori')
    def _validate_eori_gb(self, eori):
        """HMRC GB validation."""
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
            return answer[0]['valid'] is True
        except Exception as e:
            _logger.warning("GB EORI validation failed for %s: %s", eori, e)
            return False
