# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from zeep import Client
import http.client
import json


class ResPartner(models.Model):
    _inherit = "res.partner"

    eori_number = fields.Char(
        string="EORI Number",
        help="Economic Operator Registration and Identification Number used for customs identification in EU and GB."
    )

    def _split_eori(self, eori):
        """Helper function to split the EORI number into country and actual EORI number."""
        return eori[:2].upper(), eori[2:].replace(' ', '')

    @api.constrains('eori_number')
    def validate_eori_number(self):
        """Validates the EORI number based on the company's EORI validation setting."""
        if self.env.company.eori_validation:
            for partner in self:
                if partner.eori_number and not self._validate_eori(partner.eori_number):
                    raise ValidationError(_('Please verify the EORI Number.'))

    @api.model
    def _validate_eori(self, full_eori_number):
        """Validates the EORI number format and checks it against external services."""
        eori_country, eori_number = self._split_eori(full_eori_number)

        # First, handle UK and GB-specific validation
        if eori_country in ['GB', 'XI']:
            return self._validate_eori_gb(eori_country + eori_number)

        # Then, handle EU-specific validation
        country = self.env['res.country'].search([('code', '=', eori_country)], limit=1)
        europe = self.env.ref('base.europe') or self.env['res.country.group'].search([('name', '=', 'Europe')], limit=1)

        # Validate if the country is part of the EU
        if europe and country and country.id in europe.country_ids.ids:
            return self._validate_eori_eu(eori_country + eori_number)

        return False

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_eu(self, eori):
        """Validates the EORI number for EU countries using the European Commission service."""
        client = Client('https://ec.europa.eu/taxation_customs/dds2/eos/validation/services/validation?wsdl')
        result = client.service.validateEORI(eori)

        # Check if the EORI is valid based on the response from the European Commission service
        return result['result'][0]['statusDescr'] == 'Valid'

    @api.model
    @tools.ormcache('eori')
    def _validate_eori_gb(self, eori):
        """Validates the EORI number for GB using the HMRC service."""
        connection = http.client.HTTPSConnection('api.service.hmrc.gov.uk')
        connection.request(
            'POST',
            '/customs/eori/lookup/check-multiple-eori',
            json.dumps({'eoris': [eori]}),
            {'Content-type': 'application/json'}
        )
        response = connection.getresponse()

        # Handle potential errors in the request
        if response.status != 200:
            raise ValidationError(_('HMRC EORI validation failed with status code: %s' % response.status))

        answer = json.loads(response.read().decode())
        # Check if the EORI number is valid based on the HMRC response
        return answer[0]['valid'] is True
