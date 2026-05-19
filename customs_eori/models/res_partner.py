from odoo import api, fields, models, _
from zeep import Client as ZeepClient
from zeep.transports import Transport
import http.client
import json
import logging

_logger = logging.getLogger(__name__)

VALIDATION_TIMEOUT = 10  # seconds


class ResPartner(models.Model):
    _inherit = "res.partner"

    eori_validation_state = fields.Selection([
        ('unchecked', 'Unchecked'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('unavailable', 'Service Unavailable'),
    ], string='EORI Validation State', default='unchecked', readonly=True)

    eori_number = fields.Char(
        string="EORI Number",
        help="Economic Operator Registration and Identification Number used for customs identification in EU and GB."
    )

    def _split_eori(self, eori):
        return eori[:2].upper(), eori[2:].replace(' ', '')

    def _is_eori_valid(self):
        """
        Returns (is_valid, service_available) tuple.
        is_valid: True if EORI is confirmed valid, False otherwise.
        service_available: False if the external API could not be reached.
        """
        if not self.eori_number:
            return False, True
        eori_country, eori_number = self._split_eori(self.eori_number)
        full_number = eori_country + eori_number

        if eori_country in ['GB', 'XI']:
            return self._validate_eori_gb(full_number)
        else:
            country = self.env['res.country'].search([('code', '=', eori_country)], limit=1)
            europe = self.env.ref('base.europe', raise_if_not_found=False) or \
                     self.env['res.country.group'].search([('name', '=', 'Europe')], limit=1)
            if country and europe and country.id in europe.country_ids.ids:
                return self._validate_eori_eu(full_number)

        return False, True

    def validate_and_log_eori(self):
        """Validate EORI, update state, and post result in chatter."""
        for partner in self:
            if not partner.eori_number:
                partner.eori_validation_state = 'unchecked'
                continue

            is_valid, service_available = partner._is_eori_valid()

            if not service_available:
                partner.eori_validation_state = 'unavailable'
                partner.message_post(
                    body=_("EORI validation service unavailable for: %s — please retry later.") % partner.eori_number,
                    message_type="comment",
                )
            elif is_valid:
                partner.eori_validation_state = 'valid'
                partner.message_post(
                    body=_("Valid EORI Number: %s") % partner.eori_number,
                    message_type="comment",
                )
            else:
                partner.eori_validation_state = 'invalid'
                partner.message_post(
                    body=_("Invalid EORI Number: %s") % partner.eori_number,
                    message_type="comment",
                )

    @api.model
    def _validate_eori_eu(self, eori):
        """
        Validate an EU EORI via the European Commission SOAP service.
        Returns (is_valid, service_available).
        """
        try:
            transport = Transport(timeout=VALIDATION_TIMEOUT, operation_timeout=VALIDATION_TIMEOUT)
            client = ZeepClient(
                'https://ec.europa.eu/taxation_customs/dds2/eos/validation/services/validation?wsdl',
                transport=transport,
            )
            result = client.service.validateEORI(eori)
            return result['result'][0]['statusDescr'] == 'Valid', True
        except Exception as e:
            _logger.warning("EU EORI validation failed for %s: %s", eori, e)
            return False, False

    @api.model
    def _validate_eori_gb(self, eori):
        """
        Validate a GB/XI EORI via the HMRC lookup API.
        Returns (is_valid, service_available).
        """
        try:
            connection = http.client.HTTPSConnection('api.service.hmrc.gov.uk', timeout=VALIDATION_TIMEOUT)
            connection.request(
                'POST',
                '/customs/eori/lookup/check-multiple-eori',
                json.dumps({'eoris': [eori]}),
                {'Content-type': 'application/json'}
            )
            response = connection.getresponse()
            if response.status != 200:
                _logger.warning("HMRC EORI response status: %s", response.status)
                return False, False
            answer = json.loads(response.read().decode())
            return answer[0].get('valid') is True, True
        except Exception as e:
            _logger.warning("GB EORI validation failed for %s: %s", eori, e)
            return False, False

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
